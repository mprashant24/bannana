---
name: authentication-review
description: "Use this to analyze an application's authentication behavior using the provided checklist, code, and configuration."
---

## Core checklist

You must walk through these items and answer them based on the provided materials:

### Authentication Flows

- [ ] User Login  
- [ ] User Registration  
- [ ] Forgot Password  

### User Identification

- [ ] How are users identified?  
  - Username, email, password, 2FA token, etc.  
- [ ] Does the application implement strong password policies?

### Authentication Function Checks

- [ ] Password hashing mechanism  
- [ ] Timing attack resistance  
- [ ] Forgot Password security  
- [ ] Two-factor authentication  
- [ ] Enumeration protections  
- [ ] Signup security  
- [ ] Brute force protections  

### Session Management

- [ ] Session Fixation  
- [ ] Session Destruction  
- [ ] Session Length  

### Service-to-Service Authentication

- [ ] Constant-time comparison  
- [ ] Secure HMAC algorithm  
- [ ] SSL/TLS enforced  
- [ ] TLS verification not disabled  
- [ ] Reasonable TTL (≤ 1 hour typical)  
- [ ] Time skew accounted for  
- [ ] Shared secret stored securely  
- [ ] Unit tests verifying:  
  - Missing/mismatched token/HMAC/nonce  
  - Missing/expired timestamp  
  - Signature verification failure  


## How you should analyze

When this skill is active, follow these steps:

1. **Identify authentication flows**
   - Locate login, registration, and password-reset endpoints.
   - Determine what credentials are required and how they are validated.

2. **Evaluate password policies**
   - Check minimum length, complexity, blocklists, reuse prevention.
   - Confirm enforcement is server-side.

3. **Inspect password hashing**
   - Identify hashing algorithm and cost factors.
   - Flag insecure algorithms (MD5, SHA1) or missing salts.

4. **Check for timing attack resistance**
   - Look for constant-time comparison functions.
   - Flag early-return logic based on partial matches.

5. **Analyze Forgot Password flow**
   - Check token randomness, TTL, single-use behavior.
   - Ensure no user enumeration via reset endpoints.

6. **Evaluate MFA**
   - Identify TOTP/SMS/WebAuthn usage.
   - Check secret storage and rate-limiting.

7. **Check enumeration risks**
   - Compare error messages for valid vs. invalid users.
   - Look for timing differences or inconsistent status codes.

8. **Assess brute-force protections**
   - Identify rate-limiting, lockouts, CAPTCHA, or IP throttling.

9. **Review session management**
   - Check session regeneration on login.
   - Confirm logout destroys sessions or revokes tokens.
   - Evaluate TTL, idle timeout, refresh token behavior.

10. **Evaluate service-to-service authentication**
    - Check HMAC algorithms, constant-time verification, timestamp validation.
    - Confirm secrets are not hardcoded.
    - Ensure TLS is enforced and verification is not disabled.


## How you should respond

Your response should be **directly about the target application**, using this structure:

1. **Overview**
   - Brief summary of authentication posture (e.g., “strong hashing but weak session controls”).

2. **Checklist results**
   - For each item:
     - **Status:** `Pass`, `Fail`, or `Unknown`
     - **Evidence:** file names, functions, patterns
     - **Risk:** short impact description
     - **Recommendation:** concrete fix

3. **Key risks**
   - Highlight the most critical issues (e.g., insecure hashing, missing rate limits).

4. **Suggested next steps**
   - Focused, actionable improvements.

Keep language concise, technical, and directly tied to the provided code or configuration.

