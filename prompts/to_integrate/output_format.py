# --- Prompt : Output Format ---
prompt_output_format = """
### Output Format

Produce a review plan in JSON with each vulnerable function as its own section:
```json
{{
  "context_summary": "2-3 sentences summarizing what the app does and how the function works",
  "changes": [
    {{
      "function name": "vulnerable function name",
      "type": "Describe the type of vulnerability it could potentially introduce, such as authorization, authentication, etc. If it does not appear vulnerable, put N/A.",
      "status": "Describe the type of change this is to the repository, i.e. bug fix, function addition, etc.",
      "reason_for_status": "Why the function is this type of change",
      "findings": [
        {{
          "file": "file path",
          "location": "function/class name and line range",
          "observation": "What you observed in the code",
          "severity": "critical | high | medium | low",
          "confidence": "high | medium | low",
          "needs_validation": "What specifically should be verified in the next step"
        }}
      ]
    }}
  ],
  "additional_vulnerabilities": [
    {{
      "vulnerability": "descriptive_id",
      "type": "type of vulnerability",
      "reason_added": "Why this vulnerability was added based on the context",
      "findings": []
    }}
  ]
}}
```

Be specific. Cite exact file paths, function names, and line numbers.
Do NOT pad findings — only report patterns you actually see evidence for.
If a check is NOT_APPLICABLE, its findings array should be empty.
"""