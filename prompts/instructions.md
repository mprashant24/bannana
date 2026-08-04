When performing analysis, first identify tools and skills appropriate to the task.
Use tools and skills appropriate to the task.

If working files are written, they should be created in /steps/workspace
Do not create files anywhere other that /steps/workspace and /steps/final_reports (if instructed)
You can access the files in /steps/workspace to see previous analysis

If files were written, make sure to create a section in the output that
describes where they are and what they contain. This will help subsequent
analysis retrieve appropriate context

When calling a tool, you MUST output:


<tool_call>
{ "name": "<tool_name>", "arguments": { ... } }
</tool_call>

Do NOT output anything before <tool_call>.
Do NOT omit <tool_call>.
Do NOT wrap the dict in quotes.
