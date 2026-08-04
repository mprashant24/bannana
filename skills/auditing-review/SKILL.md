---
name: auditing-review
description: "Use this to analyze an application's auditing, logging, and error-handling behavior using the provided checklist, code, and configuration."
---

## Core checklist

You must walk through these items and answer them based on the provided materials:

### Secure Failure & Error Handling

- [ ] Application fails securely on exceptions  
- [ ] Error messages do not reveal sensitive details  
- [ ] Component/framework/system errors are not shown to end users  
- [ ] Security-sensitive exceptions release resources safely and roll back transactions  

### Logging Behavior

- [ ] Relevant user details and system actions are logged  
- [ ] Sensitive user input is protected and not logged  
  - Credit card numbers, SSNs, passwords, PII, keys  
- [ ] Unexpected errors and inputs are logged  
  - Multiple login attempts, invalid logins, unauthorized access attempts  
- [ ] Logs contain enough detail to reconstruct events  
- [ ] Logging configuration is adjustable via settings/env variables  
- [ ] User-controlled data is validated/sanitized before logging (log injection protection)

---

## How you should analyze

When this skill is active, follow these steps:

1. **Evaluate secure failure behavior**
   - Inspect exception handlers and error middleware.
   - Determine whether exceptions cause safe termination or unsafe partial execution.
   - Check if sensitive operations (transactions, role changes) roll back on failure.

2. **Inspect error messages**
   - Look for stack traces, SQL errors, framework internals, or file paths exposed to users.
   - Identify debug modes accidentally enabled in production.

3. **Assess logging practices**
   - Identify what events are logged (auth attempts, errors, admin actions).
   - Check whether logs include timestamps, user IDs, request IDs, and context.

4. **Check for sensitive data exposure**
   - Search for logging of passwords, tokens, PII, or secrets.
   - Confirm presence of redaction/masking utilities.

5. **Evaluate logging of unexpected inputs**
   - Look for logs capturing invalid login attempts, unauthorized access, malformed requests.

6. **Check configurability**
   - Determine whether log levels, destinations, and formats are controlled by environment variables.
   - Flag hardcoded log levels or disabled logging in production.

7. **Inspect log injection protections**
   - Ensure user-controlled data is sanitized before logging.
   - Look for newline injection, spoofed severity levels, or unescaped characters.


## How you should respond

Your response should be **directly about the target application**, using this structure:

1. **Overview**
   - Brief summary of auditing posture (e.g., “secure error handling but logs expose sensitive data”).

2. **Checklist results**
   - For each item:
     - **Status:** `Pass`, `Fail`, or `Unknown`
     - **Evidence:** file names, functions, log statements, patterns
     - **Risk:** short impact description
     - **Recommendation:** concrete fix

3. **Key risks**
   - Highlight the most critical issues (e.g., sensitive data logged, unsafe exception handling).

4. **Suggested next steps**
   - Focused, actionable improvements.

Keep language concise, technical, and tied directly to the provided code or configuration.

