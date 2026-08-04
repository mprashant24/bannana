

# ------------------------------------------------------------------------
#   Git Operations Tool
#
#   Standalone tool for isolating a specific commit diff and saving it as
#   context that a later `deepagent.py` run can analyze independently of
#   a full codebase scan.
#
#   Usage:
#     python -m tools.git_ops current
#     python -m tools.git_ops diff    --base <sha> --target <sha>
#     python -m tools.git_ops show    --commit <sha> --path <file>
#     python -m tools.git_ops analyze --base <sha> --target <sha>
# ------------------------------------------------------------------------
from argparse   import ArgumentParser
from collections import defaultdict
from datetime   import datetime, timezone
from pathlib    import Path
import json
import sys

from git     import Repo
from git.exc import BadName, GitCommandError, InvalidGitRepositoryError, NoSuchPathError



# ------------------------------------------------------------------------
#   Global Paths
# ------------------------------------------------------------------------
ROOT        = Path( __file__ ).parent.parent.resolve()
REPO_PATH   = Path( ROOT, 'repo' )
CONTEXT_DIR = Path( REPO_PATH, '.git-context' )



# ------------------------------------------------------------------------
#   Core Operations
# ------------------------------------------------------------------------
def _open_repo() -> Repo:
  try:
    return Repo( REPO_PATH )
  except ( InvalidGitRepositoryError, NoSuchPathError ) as e:
    raise RuntimeError(
      f'{REPO_PATH} is not a git repository. Check out the target codebase there first.'
    ) from e


def get_current_commit() -> str:
  return _open_repo().head.commit.hexsha


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


def get_diff_summary( base_commit:str, target_commit:str ) -> dict:
  repo = _open_repo()

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


def read_file_at_commit( path:str, commit:str ) -> str:
  repo = _open_repo()

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


def save_commit_context( commit_id:str, context_data:dict ) -> Path:
  repo = _open_repo()
  _exclude_git_context( repo )

  CONTEXT_DIR.mkdir( parents=True, exist_ok=True )
  out_path = Path( CONTEXT_DIR, f'{commit_id}.json' )

  payload = {
    'commit_id' : commit_id,
    'saved_at'  : datetime.now( timezone.utc ).isoformat(),
    **context_data,
  }

  out_path.write_text( json.dumps( payload, indent=2 ) )

  return out_path



# ------------------------------------------------------------------------
#   CLI
# ------------------------------------------------------------------------
def _cmd_current( _args ) -> None:
  print( get_current_commit() )


def _cmd_diff( args ) -> None:
  print( json.dumps( get_diff_summary( args.base, args.target ), indent=2 ) )


def _cmd_show( args ) -> None:
  print( read_file_at_commit( args.path, args.commit ) )


def _cmd_analyze( args ) -> None:
  diff_summary = get_diff_summary( args.base, args.target )
  modules      = map_changes_to_modules( diff_summary )

  context = {
    **diff_summary,
    'modules': modules,
  }

  out_path = save_commit_context( diff_summary['target_commit'], context )
  print( f'Saved commit context to {out_path}' )


def main() -> None:
  cmdline = ArgumentParser( prog='git_ops', description='Isolate and save a commit diff for independent analysis' )
  sub     = cmdline.add_subparsers( dest='command', required=True )

  sub.add_parser( 'current', help='Print the current commit SHA' ).set_defaults( func=_cmd_current )

  diff_cmd = sub.add_parser( 'diff', help='Print a diff summary between two commits' )
  diff_cmd.add_argument( '--base'  , required=True )
  diff_cmd.add_argument( '--target', required=True )
  diff_cmd.set_defaults( func=_cmd_diff )

  show_cmd = sub.add_parser( 'show', help="Print a file's content as of a given commit" )
  show_cmd.add_argument( '--commit', required=True )
  show_cmd.add_argument( '--path'  , required=True )
  show_cmd.set_defaults( func=_cmd_show )

  analyze_cmd = sub.add_parser( 'analyze', help='Compute, map, and save commit context for a diff' )
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
