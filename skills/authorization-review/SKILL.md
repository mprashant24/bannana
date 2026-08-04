---
name: authorization-review
description: "Use to analyze an application's authorization and access control behavior using the provided checklist, code, and configuration."
---


## Core checklist

For every review, you must walk through these items and try to answer them from the provided materials:

### Authorization

- [ ] Identify Roles  
- [ ] Identify sensitive/privileged endpoints  
- [ ] Identify authz expectations specific to the business purpose of the app  
  - Can non-privileged users view, add, or alter accounts?  
  - Is there functionality to add accounts with higher access levels than their own access?  
  - How is separation of duties handled?  
- [ ] Identify Authorization functions/filters  
  - Do they take Tokens? Cookies? Custom or handled by a framework?

#### Broken Access Control

- [ ] Insecure Direct Object Reference (`find_by`, `find`, `findOne`, `findAll`, etc)  
- [ ] Missing Function Level Access Control  
- [ ] Verify Authorization Filters  

#### Generic authz flaws

- [ ] Sensitive Data Exposure  
- [ ] Mass Assignment  
- [ ] Business Logic Flaws  
- [ ] Are CSRF Protections applied correctly  
- [ ] Are users forced to re-assert their credentials for requests that have critical side-effect (account changes, password reset, etc)?


## How you should analyze

When this skill is active, follow these steps:

1. **Scan for roles and permissions**
   - Look for role constants, enums, permission arrays, decorators/annotations, or policy objects.
   - Infer what each role is allowed to do (even if only partially visible).

2. **Map sensitive/privileged endpoints**
   - Identify endpoints that touch accounts, roles, financial/PII data, or irreversible actions.
   - Note how each endpoint is protected (none/authenticated/role-based/custom checks).

3. **Compare implementation to business expectations**
   - Use any provided business context to decide what *should* be allowed.
   - Highlight mismatches where code allows more than expected or fails to enforce separation of duties.

4. **Locate authorization functions/filters**
   - Identify middleware/filters/guards/policies used for authz.
   - Determine what they rely on (tokens, cookies, headers, framework principals).
   - Check whether sensitive endpoints consistently use them.

5. **Check for Broken Access Control**
   - For IDOR: find object lookups by user-supplied IDs and see if ownership/tenant checks exist.
   - For function-level access: ensure sensitive methods are not callable by any authenticated user.
   - Verify that global or route-level filters are applied and not bypassed.

6. **Evaluate generic authz flaws**
   - Sensitive data exposure: see if responses or logs leak PII, credentials, or tokens.
   - Mass assignment: look for direct binding of request bodies to models, especially for role/permission fields.
   - Business logic flaws: identify places where users can escalate privileges, bypass approvals, or violate rules.
   - CSRF: confirm protections on state-changing endpoints where relevant.
   - Re-assertion of credentials: check if critical actions require recent login or step-up auth.


## How you should respond

Your response should be **directly about the target application**, not about another LLM. Use this structure:

1. **Overview**
   - Brief summary of the authorization posture (e.g., “mixed; some endpoints well-protected, others exposed”).

2. **Checklist results**
   - For each checklist item, provide:
     - **Status:** `Pass`, `Fail`, or `Unknown`
     - **Evidence:** what you saw (file names, function names, patterns)
     - **Risk:** short impact description
     - **Recommendation:** concrete change or check to add

3. **Key risks**
   - A short list of the highest-risk findings (e.g., IDOR on account endpoints, missing role checks on admin routes).

4. **Suggested next steps**
   - Focused, actionable steps the developer or reviewer should take (e.g., “add ownership checks to X”, “enforce role Y on route Z”).

Keep language concise and technical. Do **not** instruct another LLM; act as the reviewing agent yourself.

