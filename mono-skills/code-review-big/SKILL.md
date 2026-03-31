---
name: code-review
description: This skill should be used when performing code reviews, evaluating code quality, or analyzing code for issues. It provides a structured workflow for reviewing code with focus on correctness, security, performance, maintainability, and consistency.
allowed-tools: 
disable: false
---

# Code Review Skill

A comprehensive code review skill that provides structured analysis of code quality, security vulnerabilities, performance issues, and maintainability concerns. Optimized for large-scale React + TypeScript Monorepo projects.

## When to Use

- User requests a code review or asks to review code
- User asks to check code quality or find issues in code
- User wants to analyze code for security vulnerabilities
- User asks to evaluate code before merging or deployment
- User mentions "review", "audit", "check", or "analyze" in relation to code

## Review Process

### Step 1: Gather Context

To perform an effective review, first understand the scope:

1. Identify files to review (user-specified or currently open files)
2. Understand the project context (language, framework, conventions)
3. Check for existing linter configurations and project rules
4. Determine if code is CSR (Vite) or SSR (Next.js) context

### Step 2: Analyze Code

Review code across these dimensions, in priority order:

1. **Functional Correctness** - Logic errors, edge cases, error handling
2. **Security** - XSS, credential exposure, input validation (refer to `references/security_checklist.md`)
3. **Architecture** - Component design, state management patterns (refer to `references/react_components.md`, `references/state_management.md`)
4. **Performance** - Rendering, memory leaks,  unnecessary operations, inefficient algorithms, bundle size (refer to `references/performance.md`)
5. **Type Safety** - Missing types, `any` usage, type definitions (refer to `references/typescript.md`)
6. **SSR Compliance** - Server/Client boundaries, hydration (refer to `references/nextjs_ssr.md` for Next.js code)
7. **Monorepo Health** - Package boundaries, dependencies (refer to `references/monorepo.md`)
8. **Maintainability** - Code duplication, coupling, naming, i18n

### Step 3: Generate Report

Use the report template from `references/report_template.md` to structure findings.

**IMPORTANT**: Always respond in Chinese (简体中文) when generating reports.

## Review Principles

1. **Priority Order**: Correctness > Security > Architecture > Performance > Type Safety > Maintainability
2. **Evidence-Driven**: Every issue must include precise file path and line numbers with code excerpts
3. **Actionable Solutions**: Every issue must provide concrete fix suggestions with code examples
4. **Risk Assessment**: For critical issues, quantify potential impact
5. **Context-Aware**: Consider CSR vs SSR context when reviewing

## Severity Levels

- 🔴 **Critical**: Security vulnerabilities, data loss risks, crashes, hydration errors
- 🟠 **Major**: Logic errors, performance issues, type safety violations, memory leaks
- 🟡 **Minor**: Code style, minor optimizations, documentation gaps
- 💡 **Suggestion**: Best practices, optional improvements, architecture recommendations

## Tech Stack Reference

This skill is optimized for:

| Category | Technologies |
|----------|-------------|
| Framework | React 16.14/19 + TypeScript 4.9 |
| State | RxJS + Zustand + BehaviorSubject |
| Styling | TailwindCSS (new code) + Less + styled-components |
| UI | TDesign React + Radix UI |
| Build | Vite (CSR) + Next.js 15 + Turbopack (SSR) |
| Monorepo | pnpm + Turborepo |
| i18n | i18next + react-i18next / next-intl |

## Resources

### Core Checklists
- `references/security_checklist.md` - Security vulnerability patterns
- `references/report_template.md` - Standard report format

### Architecture Checklists
- `references/react_components.md` - Component design, Props, Hooks, a11y
- `references/state_management.md` - RxJS + Zustand patterns
- `references/typescript.md` - Type safety rules

### Platform Checklists
- `references/performance.md` - Rendering, memory, bundle optimization
- `references/nextjs_ssr.md` - SSR, App Router, hydration
- `references/monorepo.md` - Package boundaries, dependencies, i18n
