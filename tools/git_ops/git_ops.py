

# ------------------------------------------------------------------------
#   Git Operations Tool
#
#   Standalone tool for isolating a specific commit diff and saving it as
#   context that a later `deepagent.py` run can analyze independently of
#   a full codebase scan.
#
#   Every operation targets a specific app checked out under repo/<app_name>/
#   (multiple apps can be checked out side by side under repo/).
#
#   Usage:
#     python -m tools.git_ops current  --app <name>
#     python -m tools.git_ops diff     --app <name> --base <sha> --target <sha>
#     python -m tools.git_ops show     --app <name> --commit <sha> --path <file>
#     python -m tools.git_ops analyze  --app <name> --base <sha> --target <sha>
# ------------------------------------------------------------------------
from argparse   import ArgumentParser
from collections import defaultdict
from datetime   import datetime, timezone
from pathlib    import Path
from typing     import Any, Dict, Optional, Type
import json
import sys

from git     import Repo
from git.exc import BadName, GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from pydantic                          import BaseModel, Field
from langchain_core.callbacks.manager  import CallbackManagerForToolRun
from langchain_core.tools              import BaseTool



# ------------------------------------------------------------------------
#   Global Paths
# ------------------------------------------------------------------------
ROOT      = Path( __file__ ).parent.parent.parent.resolve()
REPO_PATH = Path( ROOT, 'repo' )



# ------------------------------------------------------------------------
#   Core Operations
# ------------------------------------------------------------------------
def _app_repo_path( app_name:str ) -> Path:
  if not app_name or not app_name.strip():
    raise RuntimeError( 'app_name is required to locate the target repo under repo/<app_name>.' )

  repo_path = Path( REPO_PATH, app_name )
  if not repo_path.is_dir():
    raise RuntimeError(
      f'No app folder found at {repo_path}. Expected the target codebase checked out under '
      f'repo/{app_name}.'
    )

  return repo_path


def _app_context_dir( app_name:str ) -> Path:
  return Path( _app_repo_path( app_name ), '.git-context' )


def _open_repo( app_name:str ) -> Repo:
  repo_path = _app_repo_path( app_name )

  try:
    return Repo( repo_path )
  except ( InvalidGitRepositoryError, NoSuchPathError ) as e:
    raise RuntimeError(
      f'{repo_path} is not a git repository. Check out the target codebase there first.'
    ) from e


def get_current_commit( app_name:str ) -> str:
  return _open_repo( app_name ).head.commit.hexsha


def _change_type( diff ) -> str:
  # GitPython's `diff.change_type` is unreliable when create_patch=True,
  # so derive it from the boolean flags instead.
  if diff.new_file:
    return 'A'
  if diff.deleted_file:
    return 'D'
  if diff.renamed_file:
    return 'R'
  if diff.copied_file:
    return 'C'
  return diff.change_type or 'M'


def _blob_text( blob ) -> str | None:
  if blob is None:
    return None
  try:
    return blob.data_stream.read().decode( 'utf-8' )
  except UnicodeDecodeError:
    return None  # binary file


def get_diff_summary( app_name:str, base_commit:str, target_commit:str ) -> dict:
  repo = _open_repo( app_name )

  try:
    base   = repo.commit( base_commit )
    target = repo.commit( target_commit )
  except ( BadName, GitCommandError, ValueError ) as e:
    raise RuntimeError( f'Could not resolve commit(s): {e}' ) from e

  changes = []
  for diff in base.diff( target, create_patch=True ):
    try:
      patch = diff.diff.decode( 'utf-8' ) if diff.diff else None
    except UnicodeDecodeError:
      patch = None  # binary file, no textual patch

    changes.append({
      'path'        : diff.b_path or diff.a_path,
      'change_type' : _change_type( diff ),
      'old_path'    : diff.a_path,
      'new_path'    : diff.b_path,
      'patch'       : patch,
      'old_content' : _blob_text( diff.a_blob ),
      'new_content' : _blob_text( diff.b_blob ),
    })

  return {
    'base_commit'   : base.hexsha,
    'target_commit' : target.hexsha,
    'files_changed' : len( changes ),
    'changes'       : changes,
  }


def map_changes_to_modules( diff_summary:dict ) -> dict:
  modules = defaultdict( list )

  for change in diff_summary['changes']:
    parts  = Path( change['path'] ).parts
    module = parts[0] if parts else '(root)'
    modules[module].append( change['path'] )

  return dict( modules )


def read_file_at_commit( app_name:str, path:str, commit:str ) -> str:
  repo = _open_repo( app_name )

  try:
    tree = repo.commit( commit ).tree
  except ( BadName, GitCommandError, ValueError ) as e:
    raise RuntimeError( f'Could not resolve commit {commit!r}: {e}' ) from e

  try:
    blob = tree / path
  except KeyError as e:
    raise RuntimeError( f'{path!r} not found at commit {commit}' ) from e

  try:
    return blob.data_stream.read().decode( 'utf-8' )
  except UnicodeDecodeError as e:
    raise RuntimeError( f'{path!r} at commit {commit} is not valid UTF-8 (binary file?)' ) from e


def _exclude_git_context( repo:Repo ) -> None:
  """Keep .git-context/ out of the target repo's own `git status` noise."""
  exclude_file = Path( repo.git_dir, 'info', 'exclude' )
  exclude_file.parent.mkdir( parents=True, exist_ok=True )

  existing = exclude_file.read_text() if exclude_file.exists() else ''
  if '.git-context/' not in existing.splitlines():
    with exclude_file.open( 'a' ) as f:
      if existing and not existing.endswith( '\n' ):
        f.write( '\n' )
      f.write( '.git-context/\n' )


def save_commit_context( app_name:str, commit_id:str, context_data:dict ) -> Path:
  repo = _open_repo( app_name )
  _exclude_git_context( repo )

  context_dir = _app_context_dir( app_name )
  context_dir.mkdir( parents=True, exist_ok=True )
  out_path = Path( context_dir, f'{commit_id}.json' )

  payload = {
    'commit_id' : commit_id,
    'saved_at'  : datetime.now( timezone.utc ).isoformat(),
    **context_data,
  }

  out_path.write_text( json.dumps( payload, indent=2 ) )

  return out_path



# ------------------------------------------------------------------------
#   LangChain BaseTool
#
#   Action-dispatch wrapper around the functions above, following the same
#   pattern as EmbeddingSemanticSearchTool (Pydantic args_schema + a single
#   `action`-driven _run), so DeepAgent steps can call git operations
#   mid-analysis instead of only via the CLI or run_incremental_code_review.
# ------------------------------------------------------------------------
class GitOpsToolInput( BaseModel ):
  action: str = Field(
    description="The tool action to perform: 'current_commit', 'diff_summary', 'map_changes', "
                "'read_file', or 'save_context'."
  )
  app_name: str = Field(
    description="Name of the app/repo to operate on -- must match a subfolder checked out under repo/, "
                "e.g. 'vtm' for repo/vtm."
  )
  base_commit: Optional[str] = Field(
    default=None, description="Baseline commit SHA/tag. Required for 'diff_summary', 'map_changes', "
                               "and 'save_context' when context_data is not supplied directly."
  )
  target_commit: Optional[str] = Field(
    default=None, description="Target commit SHA/tag. Required for 'diff_summary', 'map_changes', "
                               "and 'save_context' when context_data is not supplied directly."
  )
  commit: Optional[str] = Field(
    default=None, description="Commit SHA/tag to read a file at. Required for 'read_file'."
  )
  path: Optional[str] = Field(
    default=None, description="Repo-relative file path to read. Required for 'read_file'."
  )
  commit_id: Optional[str] = Field(
    default=None, description="Identifier to save context under for 'save_context'. Defaults to target_commit."
  )
  context_data: Optional[Dict[str, Any]] = Field(
    default=None, description="Arbitrary JSON-serializable context to persist for 'save_context'. If "
                               "omitted, a diff + module summary for base_commit/target_commit is "
                               "computed and saved instead."
  )


class GitOpsTool( BaseTool ):
  name: str = "git_operations"
  description: str = (
    "Inspects the target repository's Git history: current HEAD commit, diff summaries between two "
    "commits (changed files, patches, before/after content), module-level change grouping, file "
    "content as of a given commit, and saving commit context snapshots for later diff runs."
  )
  args_schema: Type[GitOpsToolInput] = GitOpsToolInput

  def _run(
    self,
    action: str,
    app_name: str,
    base_commit: Optional[str] = None,
    target_commit: Optional[str] = None,
    commit: Optional[str] = None,
    path: Optional[str] = None,
    commit_id: Optional[str] = None,
    context_data: Optional[Dict[str, Any]] = None,
    run_manager: Optional[CallbackManagerForToolRun] = None,
  ) -> str:
    action = (action or '').strip().lower()

    try:
      if action == 'current_commit':
        return f'[GIT] Current commit ({app_name}): {get_current_commit( app_name )}'

      elif action == 'diff_summary':
        if not base_commit or not target_commit:
          return "[ERROR] base_commit and target_commit are required for 'diff_summary'."
        diff_summary = get_diff_summary( app_name, base_commit, target_commit )
        modules      = map_changes_to_modules( diff_summary )
        payload      = { **diff_summary, 'modules': modules }
        return f'[GIT DIFF] {app_name}: {base_commit} -> {target_commit}\n' + json.dumps( payload, indent=2 )

      elif action == 'map_changes':
        if not base_commit or not target_commit:
          return "[ERROR] base_commit and target_commit are required for 'map_changes'."
        diff_summary = get_diff_summary( app_name, base_commit, target_commit )
        modules      = map_changes_to_modules( diff_summary )
        return f'[GIT MAP] {app_name}: {base_commit} -> {target_commit}\n' + json.dumps( modules, indent=2 )

      elif action == 'read_file':
        if not path or not commit:
          return "[ERROR] path and commit are required for 'read_file'."
        content = read_file_at_commit( app_name, path, commit )
        return f'[GIT FILE] {app_name}: {path} @ {commit}\n```\n{content}\n```'

      elif action == 'save_context':
        if context_data is not None:
          resolved_commit_id = commit_id or target_commit or 'unknown'
          payload             = context_data
        else:
          if not base_commit or not target_commit:
            return (
              "[ERROR] Provide context_data, or base_commit and target_commit so a diff summary can "
              "be computed and saved, for 'save_context'."
            )
          diff_summary        = get_diff_summary( app_name, base_commit, target_commit )
          modules              = map_changes_to_modules( diff_summary )
          payload              = { **diff_summary, 'modules': modules }
          resolved_commit_id  = commit_id or diff_summary['target_commit']

        out_path = save_commit_context( app_name, resolved_commit_id, payload )
        return f'[GIT] Saved commit context to {out_path}'

      else:
        return (
          f"[ERROR] Unknown action '{action}'. Supported actions: 'current_commit', 'diff_summary', "
          "'map_changes', 'read_file', 'save_context'."
        )

    except RuntimeError as exc:
      return f'[ERROR] {exc}'



# ------------------------------------------------------------------------
#   CLI
# ------------------------------------------------------------------------
def _cmd_current( args ) -> None:
  print( get_current_commit( args.app ) )


def _cmd_diff( args ) -> None:
  print( json.dumps( get_diff_summary( args.app, args.base, args.target ), indent=2 ) )


def _cmd_show( args ) -> None:
  print( read_file_at_commit( args.app, args.path, args.commit ) )


def _cmd_analyze( args ) -> None:
  diff_summary = get_diff_summary( args.app, args.base, args.target )
  modules      = map_changes_to_modules( diff_summary )

  context = {
    **diff_summary,
    'modules': modules,
  }

  out_path = save_commit_context( args.app, diff_summary['target_commit'], context )
  print( f'Saved commit context to {out_path}' )


def main() -> None:
  cmdline = ArgumentParser( prog='git_ops', description='Isolate and save a commit diff for independent analysis' )
  sub     = cmdline.add_subparsers( dest='command', required=True )

  current_cmd = sub.add_parser( 'current', help='Print the current commit SHA' )
  current_cmd.add_argument( '--app', required=True, help='App name -- subfolder under repo/' )
  current_cmd.set_defaults( func=_cmd_current )

  diff_cmd = sub.add_parser( 'diff', help='Print a diff summary between two commits' )
  diff_cmd.add_argument( '--app'   , required=True, help='App name -- subfolder under repo/' )
  diff_cmd.add_argument( '--base'  , required=True )
  diff_cmd.add_argument( '--target', required=True )
  diff_cmd.set_defaults( func=_cmd_diff )

  show_cmd = sub.add_parser( 'show', help="Print a file's content as of a given commit" )
  show_cmd.add_argument( '--app'    , required=True, help='App name -- subfolder under repo/' )
  show_cmd.add_argument( '--commit' , required=True )
  show_cmd.add_argument( '--path'   , required=True )
  show_cmd.set_defaults( func=_cmd_show )

  analyze_cmd = sub.add_parser( 'analyze', help='Compute, map, and save commit context for a diff' )
  analyze_cmd.add_argument( '--app'   , required=True, help='App name -- subfolder under repo/' )
  analyze_cmd.add_argument( '--base'  , required=True )
  analyze_cmd.add_argument( '--target', required=True )
  analyze_cmd.set_defaults( func=_cmd_analyze )

  args = cmdline.parse_args()

  try:
    args.func( args )
  except RuntimeError as e:
    print( f'[ ERROR ]  {e}', file=sys.stderr )
    sys.exit( 1 )


if __name__ == '__main__':
  main()
