---
name: configuration-review
description: "Use to analyze an application's configuration files, framework settings, environment controls, and security-related configuration using the provided checklist, code, and documentation."
---

## Core checklist

You must walk through these items and answer them based on the provided materials:

### Configuration Files & Components

- [ ] Identify interesting configuration files  
- [ ] Identify configuration-controlled endpoints  
- [ ] Check whether those endpoints are protected by authentication/authorization  

### Framework Security Configuration

- [ ] Security protections provided by the framework are properly configured  
- [ ] Language/framework version has no known security issues  

### Security Headers

- [ ] Configuration-controlled security headers implemented  
- [ ] Security headers follow recommended best practices  

---

## How you should analyze

When this skill is active, follow these steps:

1. **Identify all configuration files**
   - Locate files controlling routing, authentication, database connections, logging, CORS, CSRF, TLS, or feature flags.
   - Identify environment-specific overrides (dev/test/prod).

2. **Evaluate configuration-controlled endpoints**
   - Look for endpoints enabled or disabled via config:
     - Admin consoles
     - Debug endpoints
     - Health/metrics endpoints
     - Feature-flagged routes
   - Check whether each is protected by:
     - Authentication
     - Authorization
     - IP restrictions
     - TLS enforcement

3. **Inspect framework security settings**
   - Identify CSRF configuration.
   - Inspect CORS rules for overly permissive origins.
   - Check cookie security flags (Secure, HttpOnly, SameSite).
   - Confirm session security settings.
   - Check rate-limiting or throttling configuration.
   - Identify whether security middleware is enabled or disabled.

4. **Evaluate language and framework versions**
   - Identify the version of the language runtime.
   - Identify the version of the framework.
   - Flag outdated or vulnerable versions.
   - Note deprecated components or missing patches.

5. **Inspect security headers**
   - Check for presence and correctness of:
     - `Content-Security-Policy`
     - `Strict-Transport-Security`
     - `X-Frame-Options`
     - `X-Content-Type-Options`
     - `Referrer-Policy`
     - `Permissions-Policy`
   - Evaluate whether headers are:
     - Present
     - Configured correctly
     - Appropriate for the environment
     - Not disabled accidentally

6. **Check for insecure configuration patterns**
   - Hardcoded secrets.
   - Debug mode enabled in production.
   - Logging of sensitive data.
   - Disabled TLS verification.
   - Overly permissive firewall or proxy rules.


## How you should respond

Your response should be **directly about the target application**, using this structure:

1. **Overview**
   - Brief summary of configuration posture (e.g., “secure defaults but missing CSP header”).

2. **Checklist results**
   - For each item:
     - **Status:** `Pass`, `Fail`, or `Unknown`
     - **Evidence:** file names, config keys, version numbers, middleware settings
     - **Risk:** short impact description
     - **Recommendation:** concrete fix

3. **Key risks**
   - Highlight the most critical issues (e.g., debug mode enabled in production).

4. **Suggested next steps**
   - Focused, actionable improvements.

Keep language concise, technical, and tied directly to the provided configuration or code.

