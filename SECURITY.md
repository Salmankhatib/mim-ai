# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | ✅ Active support  |

## Reporting a Vulnerability

If you discover a security vulnerability in MIM-AI, **please do not open a public GitHub issue**.

Instead, report it privately:

**Email:** slamankhatib06@gmail.com  
**Subject line:** `[SECURITY] mim-ai — <brief description>`

### What to include

- A clear description of the vulnerability
- Steps to reproduce (proof-of-concept or code snippet if possible)
- Potential impact assessment
- Your name / handle for acknowledgment (optional)

### Our commitment

- We will acknowledge receipt within **72 hours**
- We will investigate and respond with an estimated timeline within **7 days**
- We will issue a patch and publish a security advisory for confirmed vulnerabilities
- We will credit reporters in the release notes unless anonymity is requested

### Scope

**In scope:**
- PII leakage or bypass of the anonymizer
- Audit log tampering or hash-chain bypass
- Dependency vulnerabilities with exploitable impact
- Config injection that could expose API keys

**Out of scope:**
- Issues in third-party models or LLM provider APIs
- Theoretical issues without a practical exploit path
- Social engineering attacks

---

> MIM-AI handles potentially sensitive text (medical, legal, administrative) and is subject to Moroccan Law 09-08 data protection obligations. We take security seriously.
