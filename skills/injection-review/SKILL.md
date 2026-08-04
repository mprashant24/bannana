---
name: injection-review
description: "Use this to analyze an application's input validation, output encoding, and injection-resilience using the provided checklist, code, and configuration."
---


## Core checklist

You must walk through these items and answer them based on the provided materials:

### Input Validation

- [ ] All input validated  
- [ ] Validation uses known-good characters / proper type casting  
- [ ] Server-side validation present (not relying solely on client-side)  
- [ ] Client-side and server-side validation consistent  
- [ ] Regex-based validation used  
- [ ] Regexes use whitelists (preferred) or blacklists  
- [ ] Regex bypasses identified  
- [ ] Numeric input validated by type  
- [ ] Input length evaluated and constrained  
- [ ] Strong separation between data and commands  
- [ ] Separation between data and client-side scripts  
- [ ] Special characters checked before SQL/LDAP/XML/OS/third-party calls  
- [ ] HTTP headers validated (referrer, user-agent, custom headers)

### Output Encoding

- [ ] Parameterized queries used  
- [ ] Input validation functions encode/sanitize for output context  
- [ ] ORM functions used safely  
- [ ] Dangerous ORM functions identified (`.raw`, string interpolation)  
- [ ] Output encoding libraries identified  
- [ ] Libraries up-to-date and patched  
- [ ] Proper encoding per output context (HTML, JS, CSS, URL, JSON, XML)  
- [ ] Regex-based encoders evaluated for blind spots

### Specific Injection Vulnerabilities

- [ ] SQL / NoSQL Injection  
- [ ] NoSQL key-store manipulation (Redis, Memcache)  
- [ ] Accept-list / deny-list validation patterns


## How you should analyze

When this skill is active, follow these steps:

1. **Identify all input sources**
   - Query params, body fields, headers, cookies, file uploads.
   - Determine whether each is validated and sanitized.

2. **Evaluate validation rigor**
   - Check for type enforcement, length limits, known-good character sets.
   - Identify regexes and analyze them for bypasses or overly permissive patterns.

3. **Check separation of data and commands**
   - Inspect SQL/NoSQL queries for string concatenation.
   - Inspect OS command execution for user-controlled arguments.
   - Inspect XML/LDAP queries for unsafe interpolation.

4. **Analyze output encoding**
   - Determine whether output is encoded for its specific context.
   - Identify unsafe template rendering or direct insertion of user data.

5. **Inspect ORM usage**
   - Flag raw queries or unsafe dynamic filters.
   - Confirm parameter binding is used consistently.

6. **Evaluate specific injection risks**
   - SQL injection: look for concatenated queries, dynamic table/column names.
   - NoSQL injection: user-controlled operators or selectors.
   - Key-store manipulation: user-controlled keys or TTLs.

7. **Check forgotten HTTP components**
   - Validate headers, especially referrer and user-agent, if used in logic.


## How you should respond

Your response should be **directly about the target application**, using this structure:

1. **Overview**
   - Brief summary of injection posture (e.g., “strong input validation but unsafe raw SQL queries”).

2. **Checklist results**
   - For each item:
     - **Status:** `Pass`, `Fail`, or `Unknown`
     - **Evidence:** file names, functions, regexes, query patterns
     - **Risk:** short impact description
     - **Recommendation:** concrete fix

3. **Key risks**
   - Highlight the most critical issues (e.g., SQL injection via concatenated queries).

4. **Suggested next steps**
   - Focused, actionable improvements.

Keep language concise, technical, and tied directly to the provided code or configuration.

