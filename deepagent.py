

# ------------------------------------------------------------------------
#   Process Command Line - Do This Early to Improve 'help' Load Times
# ------------------------------------------------------------------------
from argparse import ArgumentParser
from pathlib  import Path



cmdline = ArgumentParser()
cmdline.add_argument( '-o', '--output' , type=Path, help='Output Folder')
cmdline.add_argument( '-i', '--isolate', default=False, action='store_true', help='Isolate Input Between Agents')
cmdline.add_argument( 'task'           , type=str, help='Task for the Deepagent' )

# Only parse argv when run as a script. Deferred so that importing this
# module (e.g. to use run_incremental_code_review as a tool) doesn't try
# to parse the importing process's argv.
if __name__ == '__main__':
  args = cmdline.parse_args()



# ------------------------------------------------------------------------
#   Import Dependancies
# ------------------------------------------------------------------------
from shutil   import copytree, rmtree
from textwrap import wrap
import json

from deepagents               import create_deep_agent
from deepagents.backends      import CompositeBackend, FilesystemBackend, StateBackend
from dotenv                   import load_dotenv
from langchain_aws            import ChatBedrockConverse
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts   import ChatPromptTemplate
from langchain_core.tools     import tool
from pydantic                 import BaseModel, Field

from tools.git_ops import get_diff_summary, map_changes_to_modules, save_commit_context



# ------------------------------------------------------------------------
#   Global Paths
# ------------------------------------------------------------------------
ROOT        = Path( __file__ ).parent.resolve()
PROMPT_PATH = Path( ROOT, 'prompts' )
REPO_PATH   = Path( ROOT, 'repo' )
SKILLS_PATH = Path( ROOT, 'skills' )
STEPS_PATH  = Path( ROOT, 'steps' )



# ------------------------------------------------------------------------
#   Class Definitions
# ------------------------------------------------------------------------
class DeepAgent:
  def __init__( self, model, system_prompt, backend=None, debug=False, skills=None ):
    self.system_prompt = system_prompt

    self.agent = create_deep_agent(
      model         = model,
      backend       = backend,
      skills        = skills or [],
      system_prompt = system_prompt,
      debug         = debug
    )


  def create_step( self, name:str, filename:str, isolate=False ):
    def _run( inp:str ):
      print( f'[ {name} ]  System Prompt' )
      print( self.system_prompt )

      print( f'[ {name} ]  Input' )
      print( inp )

      result = self.run( inp, name=name )

      print( '' )
      print( f'[ {name} ]  Result' )
      print( result )

      Path( STEPS_PATH, filename ).write_text( result, encoding='utf-8' )

      if isolate:
        return ''

      return result


    return RunnableLambda( _run )


  def run( self, inp:str, name='' ):
    stream = self.agent.stream({
      'messages': [
        {'role': 'user', 'content': inp}
      ]
    })


    content = ''
    tools   = []

    events = ((k,v) for event in stream for k,v in event.items())

    try:
      for key,val in events:
        if 'Middleware' in key:
          continue

        if not isinstance( val, dict ):
          continue

        if 'messages' not in val:
          continue

        for msg in val['messages']:
          if tool_calls := getattr( msg, 'tool_calls', None ):
            for tool_call in tool_calls:
              tool_name = tool_call['name']

              tools.append( tool_name )
              info = wrap( str(tool_call['args']), subsequent_indent='  ', width=30 )

              print( f'[ {name}::TOOL::{tool_name} ]  {info}\n' )


          elif not (content := getattr( msg, 'content', None )):
            continue


    except Exception as e:
      print( f'[ ERROR ]  {type(e).__name__}' )
      print( f'  Message: {str(e)[:200]}...' )
      print( f'  Tools called before error: {tools}' )

      if not content:
        content = (
          f'[TIMEOUT ERROR]\n'
          f'The agent timed out before completing.\n'
          f'Tools called: {', '.join(tools) or 'none'}\n'
        )


    return content



# ------------------------------------------------------------------------
#   Helper Functions
# ------------------------------------------------------------------------
def join_prompts( *prompts ):
  return '\n\n---\n\n'.join( prompts )


def create_prompt( personna='', task='', focus='', instructions='' ):
  personna     = f'# Personna\n{personna}'
  task         = f'# Main Task\n{task}'
  focus        = f'# Current Focus\n{focus}'
  instructions = f'# Additional Instructions\n{instructions}'

  return join_prompts( personna, task, focus, instructions )



# ------------------------------------------------------------------------
#   Pipeline Construction
# ------------------------------------------------------------------------
def build_pipeline( task:str, isolate=False, collect_focus='collect.md' ):
  rmtree( STEPS_PATH, ignore_errors=True )
  STEPS_PATH.mkdir( parents=True )

  load_dotenv()

  model = ChatBedrockConverse(
    model_id    = 'qwen.qwen3-coder-30b-a3b-v1:0',
    temperature = 0.6,
  )

  # Scope agent filesystem access to just /repo, /skills, and /steps -- NOT
  # the whole project root, which would otherwise expose .env, deepagent.py,
  # tools/, etc. to the model. Anything outside these routes resolves against
  # an empty StateBackend instead of the real filesystem.
  backend = CompositeBackend(
    default = StateBackend(),
    routes  = {
      '/repo/'  : FilesystemBackend( root_dir=str(REPO_PATH) , virtual_mode=True ),
      '/skills/': FilesystemBackend( root_dir=str(SKILLS_PATH), virtual_mode=True ),
      '/steps/' : FilesystemBackend( root_dir=str(STEPS_PATH) , virtual_mode=True ),
    },
  )

  personna     = Path( PROMPT_PATH, 'personna.md' ).read_text()
  instructions = Path( PROMPT_PATH, 'instructions.md' ).read_text()

  def make_agent( focus_file:str ) -> DeepAgent:
    return DeepAgent(
      model         = model,
      system_prompt = create_prompt(
        personna     = personna,
        task         = task,
        focus        = Path( PROMPT_PATH, focus_file ).read_text(),
        instructions = instructions
      ),
      backend       = backend,
      skills        = ['/skills'],
    )

  agent_collect = make_agent( collect_focus )
  agent_analyze = make_agent( 'analyze.md' )
  agent_review  = make_agent( 'review.md' )
  agent_report  = make_agent( 'report.md' )

  return (
    RunnableLambda(lambda task: task)
    | agent_collect.create_step( 'Collect', '1 - collect.md', isolate=isolate )
    | agent_analyze.create_step( 'Analyze', '2 - analyze.md', isolate=isolate )
    | agent_review.create_step(  'Review' , '3 - review.md', isolate=isolate )
    | agent_report.create_step(  'Report' , '4 - report.md', isolate=isolate )
  )



# ------------------------------------------------------------------------
#   Incremental Diff Review Tool
# ------------------------------------------------------------------------
class IncrementalReviewInput( BaseModel ):
  base_commit   : str = Field( description='Baseline commit SHA or tag to compare from' )
  target_commit : str = Field( description='Target commit SHA or tag containing the changes to review' )


@tool( 'run_incremental_code_review', args_schema=IncrementalReviewInput )
def run_incremental_code_review( base_commit:str, target_commit:str ) -> str:
  """Reviews the code changes between two commits in /repo (a security-focused
  review of just the diff, not the full codebase) and returns the report.

  The diff (changed files, patches, and full before/after file content) is
  computed up front via tools/git_ops.py and also saved to
  /repo/.git-context/<target_commit>.json as an audit artifact.
  """
  diff_summary = get_diff_summary( base_commit, target_commit )
  modules      = map_changes_to_modules( diff_summary )
  context      = { **diff_summary, 'modules': modules }

  save_commit_context( diff_summary['target_commit'], context )

  task = (
    'Perform a security-focused code review of a specific commit diff. '
    'You are given the changed files, their change type, unified diff patches, '
    'and full before/after file content directly in the input below -- use that '
    'instead of exploring the full codebase.'
  )

  diff_input = (
    f'Review the following commit diff (base {diff_summary["base_commit"]} -> '
    f'target {diff_summary["target_commit"]}):\n\n'
    + json.dumps( context, indent=2 )
  )

  pipeline = build_pipeline( task, collect_focus='collect_diff.md' )
  return pipeline.invoke( diff_input )



# ------------------------------------------------------------------------
#   CLI Entrypoint
# ------------------------------------------------------------------------
def main() -> None:
  pipeline = build_pipeline( args.task, isolate=args.isolate )
  pipeline.invoke( 'Analyze the codebase located under /repo' )

  if args.output:
    args.output.mkdir( exist_ok=True, parents=True )
    copytree( STEPS_PATH, args.output, dirs_exist_ok=True )

    print( '[ WARN ]  Attempted to copy all relevant outputs, but use of \n'
           '          FilesystemBackend makes it difficult to control output\n'
    )


if __name__ == '__main__':
  main()