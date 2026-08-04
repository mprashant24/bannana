

# ------------------------------------------------------------------------
#   Process Command Line - Do This Early to Improve 'help' Load Times
# ------------------------------------------------------------------------
from argparse import ArgumentParser
from pathlib  import Path



cmdline = ArgumentParser()
cmdline.add_argument( '-o', '--output' , type=Path, help='Output Folder')
cmdline.add_argument( '-i', '--isolate', default=False, action='store_true', help='Isolate Input Between Agents')
cmdline.add_argument( 'task'           , type=str, help='Task for the Deepagent' )

args = cmdline.parse_args()



# ------------------------------------------------------------------------
#   Import Dependancies
# ------------------------------------------------------------------------
from shutil   import copytree, rmtree
from textwrap import wrap

from deepagents               import create_deep_agent
from deepagents.backends      import FilesystemBackend
from dotenv                   import load_dotenv
from langchain_aws            import ChatBedrockConverse
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts   import ChatPromptTemplate



# ------------------------------------------------------------------------
#   Global Paths
# ------------------------------------------------------------------------
ROOT        = Path( __file__ ).parent.resolve()
PROMPT_PATH = Path( ROOT, 'prompts' )
SKILLS_PATH = Path( ROOT, 'skills' )
REPO_PATH   = Path( ROOT, 'repo' )
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



# ------------------------------------------------------------------------------
#   AI Chain
# ------------------------------------------------------------------------------
rmtree( STEPS_PATH )
STEPS_PATH.mkdir( parents=True )


load_dotenv()


model = ChatBedrockConverse(
  model_id    = 'qwen.qwen3-coder-30b-a3b-v1:0',
  temperature = 0.6,
)

backend = FilesystemBackend( root_dir=str(ROOT), virtual_mode=True )


personna     = Path( PROMPT_PATH, 'personna.md' ).read_text()
instructions = Path( PROMPT_PATH, 'instructions.md' ).read_text()


inventory_generate = DeepAgent(
  model         = model,
  system_prompt = create_prompt(
    personna     = personna,
    task         = args.task,
    focus        = Path( PROMPT_PATH, 'generic_collect.md' ).read_text(),
    instructions = instructions
  ),
  backend       = backend,
  skills        = [str(SKILLS_PATH)],
)


analysis_generate = DeepAgent(
  model         = model,
  system_prompt = create_prompt(
    personna     = personna,
    task         = args.task,
    focus        = Path( PROMPT_PATH, 'analysis_generate.md' ).read_text(),
    instructions = instructions
  ),
  backend       = backend,
  skills        = [str(SKILLS_PATH)],
)


analysis_validate = DeepAgent(
  model         = model,
  system_prompt = create_prompt(
    personna     = personna,
    task         = args.task,
    focus        = Path( PROMPT_PATH, 'analysis_validate.md' ).read_text(),
    instructions = instructions
  ),
  backend       = backend,
  skills        = [str(SKILLS_PATH)],
)


report_generate = DeepAgent(
  model         = model,
  system_prompt = create_prompt(
    personna     = personna,
    task         = args.task,
    focus        = Path( PROMPT_PATH, 'report_generate.md' ).read_text(),
    instructions = instructions
  ),
  backend       = backend,
  skills        = [str(SKILLS_PATH)],
)


report_validate = DeepAgent(
  model         = model,
  system_prompt = create_prompt(
    personna     = personna,
    task         = args.task,
    focus        = Path( PROMPT_PATH, 'generic_validate.md' ).read_text(),
    instructions = instructions
  ),
  backend       = backend,
  skills        = [str(SKILLS_PATH)],
)


report_save = DeepAgent(
  model         = model,
  system_prompt = create_prompt(
    personna     = personna,
    task         = args.task,
    focus        = Path( PROMPT_PATH, 'report_save.md' ).read_text(),
    instructions = instructions
  ),
  backend       = backend,
  skills        = [str(SKILLS_PATH)],
)


chain = (
  RunnableLambda(lambda task: task)
  | inventory_generate.create_step( 'InventoryGenerate', '1 - inventory_generate.md', isolate=args.isolate )
  | analysis_generate.create_step(  'AnalysisGenerate' , '2 - analysis_generate.md' , isolate=args.isolate )
  | analysis_validate.create_step(  'AnalysisValidate' , '3 - analysis_validate.md' , isolate=args.isolate )
  | report_generate.create_step(    'ReportGenerate'   , '4 - report_generate.md'   , isolate=args.isolate )
  | report_validate.create_step(    'ReportValidate'   , '5 - report_validate.md'   , isolate=args.isolate )
  | report_save.create_step(        'ReportSave'       , '6 - report_save.md'       , isolate=args.isolate )
)


chain.invoke( 'Analyze the codebase located under /repo' )


if args.output:
  args.output.mkdir( exist_ok=True, parents=True )
  copytree( STEPS_PATH, args.output, dirs_exist_ok=True )
  
  print( '[ WARN ]  Attempted to copy all relevant outputs, but use of \n'
         '          FilesystemBackend makes it difficult to control output\n'
  )