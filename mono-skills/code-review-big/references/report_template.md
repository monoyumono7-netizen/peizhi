# Code Review Report Template

Use this template to structure code review findings.

---

## Overall Assessment

✅ / ⚠️ / ❌ [Excellent / Good / Needs Improvement]

*Brief summary of main strengths and key risks (no more than 3 sentences).*

---

## Issue List

*(Sorted by severity: 🔴 Critical, 🟠 Major, 🟡 Minor, 💡 Suggestion)*

### {Number}. {Issue Type} {Severity Marker}

**Location**: `{file_path}#L{start_line}-L{end_line}`

**Analysis**: Concise description of root cause and impact.

**Fix Suggestion**:

```{language}
// FILEPATH: {full_file_path}

// ------ Original Code ------
{original code block - must be exact}
// ----------------------------

// ------ Fixed Code ------
{improved code block}
// ------------------------
```

---

## Example Issue

### 1. TypeScript Type Safety 🔴

**Location**: `src/components/Chat/ChatInput.tsx#L45-L48`

**Analysis**: Uses `any` type, violating TypeScript conventions and potentially causing runtime type errors.

**Fix Suggestion**:

```typescript
// FILEPATH: src/components/Chat/ChatInput.tsx

// ------ Original Code ------
const handleSubmit = (data: any) => {
  sendMessage(data);
};
// ----------------------------

// ------ Fixed Code ------
interface MessageData {
  content: string;
  attachments?: string[];
}

const handleSubmit = (data: MessageData): void => {
  sendMessage(data);
};
// ------------------------
```

---

## Summary Statistics

| Severity | Count |
|----------|-------|
| 🔴 Critical | 0 |
| 🟠 Major | 0 |
| 🟡 Minor | 0 |
| 💡 Suggestion | 0 |

---

## Recommendations

*List top 3 priority items to address before merge.*
