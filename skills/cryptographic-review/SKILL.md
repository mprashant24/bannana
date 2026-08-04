---
name: cryptographic-review
description: "Use to analyze an application's cryptographic usage, cipher strength, key protection, and protocol security using the provided checklist, code, and configuration."
---

## Core checklist

You must walk through these items and answer them based on the provided materials:

### Cryptographic Library Usage

- [ ] Identify standard encryption libraries used  
  - Hashing functions (password hashing, signing)  
  - Encryption functions (data storage, communications)

### Cipher Strength

- [ ] Ciphers meet industry standards  
  - Less than 256‑bit encryption  
  - MD5/SHA1 for password hashing  
- [ ] Any RC4 stream ciphers  
- [ ] Certificates with <1024‑bit keys  
- [ ] SSL protocol versions present

### Key & Secret Protection

- [ ] Cryptographic private keys protected  
- [ ] Passwords protected  
- [ ] Secrets protected (not hardcoded, not logged, not exposed)


## How you should analyze

When this skill is active, follow these steps:

1. **Identify cryptographic primitives**
   - Locate hashing, encryption, signing, and HMAC functions.
   - Determine which libraries are used (e.g., OpenSSL, crypto module, BouncyCastle).

2. **Evaluate hashing mechanisms**
   - Check for secure password hashing (bcrypt, scrypt, Argon2, PBKDF2).
   - Flag insecure algorithms (MD5, SHA1).
   - Check for salts and appropriate cost factors.

3. **Evaluate encryption mechanisms**
   - Identify symmetric/asymmetric algorithms.
   - Check key sizes (AES‑256, RSA‑2048, ECC‑256).
   - Flag deprecated algorithms (DES, 3DES, RC4).

4. **Inspect certificate and protocol configuration**
   - Check certificate key lengths.
   - Identify supported TLS versions.
   - Flag SSLv2, SSLv3, TLS 1.0/1.1.
   - Check for disabled certificate verification.

5. **Check key and secret protection**
   - Identify where secrets are stored:
     - Environment variables
     - Vaults
     - Config files
     - Hardcoded in source
   - Flag any hardcoded secrets or private keys.
   - Check file permissions for key files.

6. **Inspect cryptographic misuse patterns**
   - Look for:
     - Non‑cryptographic RNGs (`Math.random`, `rand()`)
     - AES‑ECB mode
     - Static IVs or salts
     - Reused nonces
     - Custom crypto implementations

7. **Evaluate communication security**
   - Check HMAC algorithms (SHA‑256 or better).
   - Confirm constant‑time comparison for signatures.
   - Check timestamp validation and replay protection.
   - Ensure TLS is enforced and verification is not disabled.


## How you should respond

Your response should be **directly about the target application**, using this structure:

1. **Overview**
   - Brief summary of cryptographic posture (e.g., “modern hashing but weak TLS configuration”).

2. **Checklist results**
   - For each item:
     - **Status:** `Pass`, `Fail`, or `Unknown`
     - **Evidence:** file names, functions, algorithms, key sizes
     - **Risk:** short impact description
     - **Recommendation:** concrete fix

3. **Key risks**
   - Highlight the most critical issues (e.g., MD5 hashing, hardcoded private keys).

4. **Suggested next steps**
   - Focused, actionable improvements.

Keep language concise, technical, and tied directly to the provided code or configuration.

