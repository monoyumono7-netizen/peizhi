# TypeScript Checklist

Guidelines for reviewing TypeScript code quality and type safety.

## Type Safety

### No `any` 🔴

```tsx
// ❌ Bad: Using any
const handleData = (data: any) => { ... };
const response: any = await fetch('/api');
const items = [] as any[];

// ✅ Good: Proper types
interface UserData {
  id: string;
  name: string;
}

const handleData = (data: UserData) => { ... };
const response: ApiResponse<User> = await fetch('/api');
const items: User[] = [];
```

### Avoid Type Assertions 🟠

```tsx
// ❌ Bad: Unsafe type assertion
const user = response as User; // What if response is null?
const element = document.getElementById('app') as HTMLDivElement;

// ✅ Good: Type guards
function isUser(data: unknown): data is User {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    'name' in data
  );
}

if (isUser(response)) {
  // response is User here
}

// ✅ Good: Null checks
const element = document.getElementById('app');
if (element instanceof HTMLDivElement) {
  // element is HTMLDivElement here
}
```

### Unknown vs Any 🟠

```tsx
// ❌ Bad: any for unknown data
const parseJSON = (str: string): any => JSON.parse(str);

// ✅ Good: unknown forces type checking
const parseJSON = (str: string): unknown => JSON.parse(str);

const data = parseJSON('{"name": "John"}');
// Must narrow type before use
if (isUser(data)) {
  console.log(data.name);
}
```

### Non-null Assertion 🔴

```tsx
// ❌ Bad: Non-null assertion without guarantee
const user = users.find(u => u.id === id)!;
const element = document.querySelector('.btn')!;

// ✅ Good: Handle null case
const user = users.find(u => u.id === id);
if (!user) {
  throw new Error(`User ${id} not found`);
}

// ✅ Good: Optional chaining
const element = document.querySelector('.btn');
element?.addEventListener('click', handleClick);
```

## Function Types

### Explicit Return Types 🟠

```tsx
// ❌ Bad: Implicit return type
const getUser = async (id: string) => {
  const response = await fetch(`/api/users/${id}`);
  return response.json();
}; // Return type is Promise<any>!

// ✅ Good: Explicit return type
const getUser = async (id: string): Promise<User> => {
  const response = await fetch(`/api/users/${id}`);
  return response.json();
};

// ✅ Good: Explicit for public APIs, infer for internals
export const publicFunction = (x: number): number => x * 2;
const internalHelper = (x: number) => x * 2; // OK to infer
```

### Function Overloads 🟡

```tsx
// ✅ Good: Overloads for different return types
function parse(input: string): string[];
function parse(input: string, asObject: true): Record<string, string>;
function parse(input: string, asObject?: boolean) {
  if (asObject) {
    return Object.fromEntries(input.split(',').map(s => s.split('=')));
  }
  return input.split(',');
}

const arr = parse('a,b,c'); // string[]
const obj = parse('a=1,b=2', true); // Record<string, string>
```

## Generics

### Generic Constraints 🟠

```tsx
// ❌ Bad: Unconstrained generic
const getProperty = <T>(obj: T, key: string) => obj[key];
// Error: Type 'string' cannot be used to index type 'T'

// ✅ Good: Constrained generic
const getProperty = <T extends object, K extends keyof T>(
  obj: T,
  key: K
): T[K] => obj[key];

const user = { name: 'John', age: 30 };
const name = getProperty(user, 'name'); // string
const age = getProperty(user, 'age'); // number
```

### Avoid Excessive Generics 🟡

```tsx
// ❌ Bad: Over-engineered generics
const identity = <T extends U, U extends V, V>(x: T): T => x;

// ✅ Good: Simple and clear
const identity = <T>(x: T): T => x;
```

### Generic Defaults 🟡

```tsx
// ✅ Good: Provide sensible defaults
interface ApiResponse<T = unknown> {
  data: T;
  status: number;
}

// Can use without specifying type
const response: ApiResponse = await fetch('/api');

// Or specify type
const userResponse: ApiResponse<User> = await fetch('/api/user');
```

## Utility Types

### Prefer Built-in Utilities 🟡

```tsx
// ❌ Bad: Manual type construction
interface PartialUser {
  id?: string;
  name?: string;
  email?: string;
}

// ✅ Good: Use Partial
type PartialUser = Partial<User>;

// Common utilities
type ReadonlyUser = Readonly<User>;
type UserKeys = keyof User;
type PickedUser = Pick<User, 'id' | 'name'>;
type OmittedUser = Omit<User, 'password'>;
type RequiredUser = Required<PartialUser>;
type UserRecord = Record<string, User>;
```

### Conditional Types 🟡

```tsx
// ✅ Good: Extract and Exclude
type StringOrNumber = string | number;
type JustString = Extract<StringOrNumber, string>; // string
type JustNumber = Exclude<StringOrNumber, string>; // number

// ✅ Good: NonNullable
type MaybeUser = User | null | undefined;
type DefiniteUser = NonNullable<MaybeUser>; // User
```

## Interface vs Type

### When to Use Interface 🟡

```tsx
// ✅ Good: Interface for object shapes (extensible)
interface User {
  id: string;
  name: string;
}

interface AdminUser extends User {
  permissions: string[];
}

// ✅ Good: Declaration merging
interface Window {
  myCustomProperty: string;
}
```

### When to Use Type 🟡

```tsx
// ✅ Good: Type for unions, intersections, primitives
type Status = 'pending' | 'active' | 'inactive';
type ID = string | number;
type UserWithMeta = User & { meta: Metadata };

// ✅ Good: Type for computed types
type UserKeys = keyof User;
type ReadonlyUser = Readonly<User>;
```

## Discriminated Unions 🟠

```tsx
// ❌ Bad: Loose union
interface ApiResult {
  success: boolean;
  data?: User;
  error?: string;
}

// ✅ Good: Discriminated union
type ApiResult =
  | { success: true; data: User }
  | { success: false; error: string };

const handleResult = (result: ApiResult) => {
  if (result.success) {
    // TypeScript knows result.data exists
    console.log(result.data.name);
  } else {
    // TypeScript knows result.error exists
    console.log(result.error);
  }
};
```

## Strict Mode 🔴

### Required Compiler Options

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    // Or individually:
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    
    // Additional safety
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitOverride": true
  }
}
```

### noUncheckedIndexedAccess 🟠

```tsx
// With noUncheckedIndexedAccess: true
const arr = [1, 2, 3];
const item = arr[0]; // number | undefined

// ❌ Bad: Ignoring undefined
const doubled = item * 2; // Error!

// ✅ Good: Handle undefined
if (item !== undefined) {
  const doubled = item * 2;
}

// Or use non-null assertion if you're sure
const doubled = item! * 2;
```

## React-Specific Types 🟠

```tsx
// ✅ Good: Proper React types
interface ButtonProps {
  children: React.ReactNode;
  onClick: React.MouseEventHandler<HTMLButtonElement>;
  className?: string;
}

// ✅ Good: Extending HTML attributes
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

// ✅ Good: ForwardRef types
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, ...props }, ref) => (
    <div>
      <label>{label}</label>
      <input ref={ref} {...props} />
      {error && <span>{error}</span>}
    </div>
  )
);

// ✅ Good: Event handler types
const handleChange: React.ChangeEventHandler<HTMLInputElement> = (e) => {
  setValue(e.target.value);
};

const handleSubmit: React.FormEventHandler<HTMLFormElement> = (e) => {
  e.preventDefault();
  // ...
};
```

## Zod Integration 🟡

```tsx
import { z } from 'zod';

// ✅ Good: Schema-first approach
const UserSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  email: z.string().email(),
  age: z.number().int().positive().optional(),
});

// Infer TypeScript type from schema
type User = z.infer<typeof UserSchema>;

// Runtime validation
const parseUser = (data: unknown): User => {
  return UserSchema.parse(data);
};

// Safe parsing
const result = UserSchema.safeParse(data);
if (result.success) {
  // result.data is User
} else {
  // result.error contains validation errors
}
```
