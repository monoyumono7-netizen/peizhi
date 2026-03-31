# Monorepo Checklist

Guidelines for reviewing Monorepo architecture with pnpm workspaces and Turborepo.

## Package Dependencies

### Dependency Direction 🔴

```
✅ Correct dependency flow:
frontend-web → common-workspace → common-react-components
            → common-editor     → common-schema

❌ Wrong: common packages should NOT depend on frontend packages
common-workspace → frontend-web  // WRONG!
```

**Check for**:
- Common/shared packages importing from app packages
- Circular dependencies between packages
- Upward dependencies (shared → app)

```tsx
// ❌ Bad: common package importing from frontend
// packages/common/workspace/src/utils.ts
import { AppConfig } from '@frontend/web/config'; // WRONG!

// ✅ Good: frontend imports from common
// packages/frontend/web/src/app.tsx
import { WorkspaceUtils } from '@common/workspace';
```

### Circular Dependencies 🔴

```tsx
// ❌ Bad: Circular import
// packages/common/editor/src/index.ts
import { Schema } from '@common/schema';

// packages/common/schema/src/index.ts
import { EditorUtils } from '@common/editor'; // Circular!

// ✅ Good: Extract shared types to separate package
// packages/common/types/src/index.ts
export interface EditorSchema { ... }

// Both packages import from types
import { EditorSchema } from '@common/types';
```

### Workspace Protocol 🟠

```json
// ❌ Bad: Hardcoded versions for internal packages
{
  "dependencies": {
    "@common/workspace": "1.0.0"
  }
}

// ✅ Good: Use workspace protocol
{
  "dependencies": {
    "@common/workspace": "workspace:*"
  }
}
```

### Peer Dependencies 🟠

```json
// ❌ Bad: React as direct dependency in shared component library
// packages/common/react-components/package.json
{
  "dependencies": {
    "react": "^18.0.0"
  }
}

// ✅ Good: React as peer dependency
{
  "peerDependencies": {
    "react": "^16.14.0 || ^17.0.0 || ^18.0.0 || ^19.0.0"
  },
  "devDependencies": {
    "react": "^18.0.0"
  }
}
```

### Version Consistency 🟠

```json
// ❌ Bad: Different versions across packages
// packages/frontend-web/package.json
{ "dependencies": { "lodash": "^4.17.21" } }

// packages/common-workspace/package.json
{ "dependencies": { "lodash": "^4.17.15" } }

// ✅ Good: Use pnpm catalog or syncpack
// pnpm-workspace.yaml
catalog:
  lodash: ^4.17.21
  react: ^18.2.0

// package.json
{ "dependencies": { "lodash": "catalog:" } }
```

## Shared Code Design

### Export Boundaries 🟠

```tsx
// ❌ Bad: Exposing internal implementation
// packages/common/workspace/src/index.ts
export * from './internal/helpers';
export * from './internal/utils';
export * from './components/Button';

// ✅ Good: Explicit public API
// packages/common/workspace/src/index.ts
export { Button } from './components/Button';
export type { ButtonProps } from './components/Button';
// Internal helpers stay internal
```

### Type Exports 🟠

```tsx
// ❌ Bad: Missing type exports
// packages/common/schema/src/index.ts
export const createSchema = () => { ... };
// Types not exported!

// ✅ Good: Export types alongside values
// packages/common/schema/src/index.ts
export { createSchema } from './create-schema';
export type { Schema, SchemaConfig } from './types';
```

### Package Entry Points 🟡

```json
// ❌ Bad: Single entry point for large package
{
  "main": "./dist/index.js"
}
// Imports everything: import { tiny } from '@common/huge-package';

// ✅ Good: Multiple entry points (exports map)
{
  "exports": {
    ".": "./dist/index.js",
    "./utils": "./dist/utils/index.js",
    "./components": "./dist/components/index.js"
  }
}
// Selective imports: import { tiny } from '@common/huge-package/utils';
```

## Turborepo Configuration

### Task Dependencies 🟠

```json
// turbo.json
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    },
    "test": {
      "dependsOn": ["build"],
      "outputs": []
    },
    "lint": {
      "outputs": []
    },
    "dev": {
      "cache": false,
      "persistent": true
    }
  }
}
```

**Check for**:
- `^build` for dependencies that need to build first
- Correct `outputs` for cache invalidation
- `cache: false` for dev servers

### Build Order 🔴

```json
// ❌ Bad: Missing dependency declaration
{
  "pipeline": {
    "build": {
      "outputs": ["dist/**"]
      // Missing dependsOn: ["^build"]!
    }
  }
}
// common-workspace might build before common-schema it depends on

// ✅ Good: Explicit dependency chain
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    }
  }
}
```

### Cache Configuration 🟡

```json
// turbo.json
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**"],
      "inputs": [
        "src/**",
        "package.json",
        "tsconfig.json"
      ]
    }
  },
  "globalDependencies": [
    ".env",
    "tsconfig.base.json"
  ]
}
```

## i18n in Monorepo 🟡

### Key Naming Convention

```json
// ❌ Bad: Flat, conflicting keys
{
  "save": "Save",
  "cancel": "Cancel",
  "title": "Title"
}

// ✅ Good: Namespaced keys
{
  "common": {
    "actions": {
      "save": "Save",
      "cancel": "Cancel"
    }
  },
  "workspace": {
    "editor": {
      "title": "Editor Title"
    }
  }
}
```

### Shared Translations 🟠

```
packages/
├── common/
│   └── i18n/
│       └── locales/
│           ├── en/
│           │   └── common.json    # Shared translations
│           └── zh/
│               └── common.json
├── frontend-web/
│   └── locales/
│       ├── en/
│       │   └── app.json          # App-specific
│       └── zh/
│           └── app.json
```

### Plural Handling 🟡

```json
// ❌ Bad: Missing plural forms
{
  "items": "{{count}} items"
}

// ✅ Good: Proper plural handling (ICU format)
{
  "items": "{count, plural, =0 {No items} one {# item} other {# items}}"
}

// Or i18next format
{
  "items_zero": "No items",
  "items_one": "{{count}} item",
  "items_other": "{{count}} items"
}
```

### Missing Translation Detection 🟡

```tsx
// ✅ Good: Configure i18next to warn on missing keys
i18next.init({
  saveMissing: true,
  missingKeyHandler: (lng, ns, key) => {
    console.warn(`Missing translation: ${lng}/${ns}/${key}`);
  },
});

// ✅ Good: Use TypeScript for type-safe translations
// types/i18next.d.ts
import 'i18next';
import en from '../locales/en/common.json';

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common';
    resources: {
      common: typeof en;
    };
  }
}
```

## Cross-Package Testing 🟡

```json
// packages/common/workspace/package.json
{
  "scripts": {
    "test": "vitest",
    "test:integration": "vitest --config vitest.integration.config.ts"
  }
}

// Root package.json
{
  "scripts": {
    "test": "turbo run test",
    "test:affected": "turbo run test --filter=...[origin/main]"
  }
}
```

## Import Aliases 🟡

```json
// tsconfig.base.json (root)
{
  "compilerOptions": {
    "paths": {
      "@common/*": ["packages/common/*/src"],
      "@frontend/*": ["packages/frontend/*/src"]
    }
  }
}

// packages/frontend-web/tsconfig.json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"],
      "@common/*": ["../../common/*/src"]
    }
  }
}
```

## Package Boundaries Checklist

| Check | Description |
|-------|-------------|
| ✅ No upward deps | Common packages don't import from app packages |
| ✅ No circular deps | No A → B → A dependency chains |
| ✅ Explicit exports | Public API is intentionally exposed |
| ✅ Type exports | Types are exported for consumers |
| ✅ Peer deps | React/shared libs are peer dependencies |
| ✅ Version sync | Same dependency versions across packages |
| ✅ Build order | Turborepo pipeline respects dependencies |
