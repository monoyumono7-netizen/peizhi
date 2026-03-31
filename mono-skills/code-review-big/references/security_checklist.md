# Security Checklist

A comprehensive checklist of security vulnerabilities to identify during code review, with focus on frontend security.

## Cross-Site Scripting (XSS) 🔴

**Pattern**: Unescaped user input rendered in HTML

### React-Specific XSS

```tsx
// ❌ Vulnerable: dangerouslySetInnerHTML without sanitization
<div dangerouslySetInnerHTML={{ __html: userInput }} />

// ❌ Vulnerable: href with user input
<a href={userInput}>Click</a>  // javascript:alert(1)

// ❌ Vulnerable: Dynamic attribute injection
<div {...userControlledProps} />

// ✅ Safe: Use textContent or React's default escaping
<div>{userInput}</div>

// ✅ Safe: Sanitize HTML with DOMPurify
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />

// ✅ Safe: Validate URLs
const isSafeUrl = (url: string) => {
  try {
    const parsed = new URL(url);
    return ['http:', 'https:'].includes(parsed.protocol);
  } catch {
    return false;
  }
};
<a href={isSafeUrl(userInput) ? userInput : '#'}>Click</a>
```

### DOM XSS

```javascript
// ❌ Vulnerable
element.innerHTML = userInput;
element.outerHTML = userInput;
document.write(userInput);
eval(userInput);

// ✅ Safe
element.textContent = userInput;
```

**Check for**:
- `innerHTML`, `outerHTML` with user data
- `dangerouslySetInnerHTML` without sanitization
- `v-html` in Vue without sanitization
- URL parameters reflected in page content
- `javascript:` URLs in href/src attributes
- Dynamic script/style injection

## Cross-Site Request Forgery (CSRF) 🔴

**Pattern**: State-changing requests without CSRF protection

```tsx
// ❌ Vulnerable: No CSRF token
const deleteUser = async (id: string) => {
  await fetch(`/api/users/${id}`, { method: 'DELETE' });
};

// ✅ Safe: Include CSRF token
const deleteUser = async (id: string) => {
  await fetch(`/api/users/${id}`, {
    method: 'DELETE',
    headers: {
      'X-CSRF-Token': getCsrfToken(),
    },
  });
};

// ✅ Safe: Use SameSite cookies
// Server sets: Set-Cookie: session=xxx; SameSite=Strict; Secure; HttpOnly
```

**Check for**:
- State-changing requests (POST, PUT, DELETE) without CSRF tokens
- Missing SameSite cookie attribute
- CORS misconfiguration allowing credentials

## Credential Exposure 🔴

**Pattern**: Secrets exposed in frontend code

```tsx
// ❌ Vulnerable: API keys in frontend code
const API_KEY = 'sk-1234567890abcdef';
const stripe = new Stripe(API_KEY);

// ❌ Vulnerable: Secrets in environment variables exposed to client
// .env
NEXT_PUBLIC_SECRET_KEY=sk-secret  // NEXT_PUBLIC_ is exposed!

// ✅ Safe: Use backend proxy for sensitive operations
const createPayment = async () => {
  // Call your backend, which has the secret key
  await fetch('/api/payments', { method: 'POST' });
};

// ✅ Safe: Only public keys in frontend
const STRIPE_PUBLIC_KEY = 'pk-1234567890';  // Public key is OK
```

**Check for**:
- API keys, tokens, passwords in frontend code
- Secrets in `NEXT_PUBLIC_*` or `VITE_*` environment variables
- Secrets in committed configuration files or sample configs
- Secrets in environment variable default values
- Private keys in client bundles
- Credentials in git history

## Sensitive Data in Storage 🟠

**Pattern**: Sensitive data in browser storage

```tsx
// ❌ Vulnerable: Sensitive data in localStorage
localStorage.setItem('authToken', token);
localStorage.setItem('creditCard', cardNumber);

// ❌ Vulnerable: Sensitive data in URL
window.location.href = `/dashboard?token=${authToken}`;

// ✅ Safe: Use HttpOnly cookies for auth tokens
// Server sets: Set-Cookie: token=xxx; HttpOnly; Secure; SameSite=Strict

// ✅ Safe: Use sessionStorage for temporary sensitive data
sessionStorage.setItem('tempData', data);
// And clear on logout
sessionStorage.clear();
```

**Check for**:
- Auth tokens in localStorage (vulnerable to XSS)
- Sensitive data in URL parameters (logged, cached, shared)
- PII stored client-side without encryption
- Sensitive data in Redux DevTools / state snapshots

## Input Validation 🟠

**Pattern**: Missing or insufficient validation

```tsx
// ❌ Vulnerable: No validation
const UserForm = () => {
  const handleSubmit = (data: FormData) => {
    createUser(data); // What if email is invalid?
  };
};

// ✅ Safe: Validate with Zod
import { z } from 'zod';

const UserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
  age: z.number().int().min(0).max(150),
});

const handleSubmit = (data: unknown) => {
  const result = UserSchema.safeParse(data);
  if (!result.success) {
    setErrors(result.error.flatten());
    return;
  }
  createUser(result.data);
};
```

**Check for**:
- User input used directly without validation
- Missing length limits (DoS via large payloads)
- Missing type validation
- Path traversal in file operations
- Command injection in shell commands (e.g., exec/spawn with untrusted input)

## Prototype Pollution 🟠

**Pattern**: Unsafe object merging

```tsx
// ❌ Vulnerable: Deep merge without protection
const merge = (target, source) => {
  for (const key in source) {
    target[key] = source[key];  // Can set __proto__!
  }
};

// ❌ Vulnerable: JSON.parse without validation
const config = JSON.parse(userInput);
// userInput: {"__proto__": {"isAdmin": true}}

// ✅ Safe: Use Object.hasOwn or whitelist
const safeMerge = (target, source) => {
  for (const key in source) {
    if (Object.hasOwn(source, key) && key !== '__proto__') {
      target[key] = source[key];
    }
  }
};

// ✅ Safe: Use libraries with protection
import { merge } from 'lodash'; // Has prototype pollution protection
```

## Dependency Vulnerabilities 🟡

**Check for**:
- Known vulnerabilities: `pnpm audit`
- Outdated dependencies with security patches
- Typosquatting packages (e.g., `lodash` vs `1odash`)
- Unnecessary dependencies increasing attack surface

```bash
# Regular security audits
pnpm audit
pnpm audit --fix

# Check for outdated packages
pnpm outdated
```

## Content Security Policy (CSP) 💡

```tsx
// next.config.js - Recommended CSP headers
const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline'",  // Avoid if possible
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "connect-src 'self' https://api.example.com",
      "frame-ancestors 'none'",
    ].join('; '),
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY',
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff',
  },
];
```

## SQL Injection (Backend) 🔴

**Pattern**: User input concatenated into SQL queries

```javascript
// ❌ Vulnerable
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// ✅ Safe: Parameterized query
const query = 'SELECT * FROM users WHERE id = ?';
db.query(query, [userId]);
```

**Check for**:
- String concatenation in SQL statements
- Template literals with user input in queries
- Dynamic table/column names without whitelist validation
- ORM raw queries with unescaped input

## Authentication & Authorization 🔴

**Check for**:
- Missing authentication on sensitive endpoints
- Broken access control (users accessing others' data)
- JWT stored in localStorage (use HttpOnly cookies)
- Missing token expiration
- Session management issues (session fixation, invalidation on logout, rotation after privilege changes)
- Insecure password storage (not using bcrypt/argon2)

## Sensitive Data Handling 🟠

**Check for**:
- Logging sensitive information (passwords, tokens, PII)
- Sensitive data in error messages shown to users
- Unencrypted transmission (ensure HTTPS)
- PII in analytics/tracking events
