Build me a project plan for goal where we are updating this deep agent and adding 2 execution modes. 
- Baseline - to analyze the full repo to build output that will be used for diff execution. The output will include the inventory of technology, risk area (form the supported analysis list) to support the following steps and future execution to save time and reduce the tokens.
- diff - This mode will take the repo commit id and compare againt the previous report commit, generate inventory refresh and type of change analysis. This change analysis will select the scope of analysis like authz/authn analysis only because type of chnage has added, significnatly modified or deleted the authz/authn related code. 

There will be 3 tools that will support the deep aganet to speed up the execution and reduce the token cose to do the AI base security code review. 
- Git openrations - provide the git diff changes file list and related info. Save the context for future run. 
- Embedding - Generate embedding to be used for inventory generation technology and potential risk
- Reporting - This toll will help consitency of output by the deep agent and report generation for both mode. Also help refresh removal of identified issues. 

Deep agent will have following steps
- Inventory generation (Technology and Risk)
- Scope of analysis detection
- Execution of Analysis
- Validating/Judging the results
- Generation of report
- Validation/Judging of the report
- Saving the context for future run