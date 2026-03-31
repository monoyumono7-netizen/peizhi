# React Components Checklist

Guidelines for reviewing React component design, Props, Hooks, and accessibility.

## Component Design

### Component Split Signals 🔴

A component should be split when:

- **Lines exceed 200**: File is too large to maintain
- **useState count > 5**: Too much local state, consider extraction
- **Nesting depth > 3**: JSX is too deeply nested
- **Multiple responsibilities**: Component does more than one thing

```tsx
// ❌ Bad: Monolithic component
const UserDashboard = () => {
  const [user, setUser] = useState();
  const [posts, setPosts] = useState();
  const [comments, setComments] = useState();
  const [notifications, setNotifications] = useState();
  const [settings, setSettings] = useState();
  // ... 300+ lines
};

// ✅ Good: Split by responsibility
const UserDashboard = () => (
  <DashboardLayout>
    <UserProfile />
    <UserPosts />
    <UserNotifications />
  </DashboardLayout>
);
```

### Container/Presentational Pattern

```tsx
// ✅ Container: handles logic and data
const UserListContainer = () => {
  const users = useUsers();
  const handleDelete = useCallback((id: string) => {
    deleteUser(id);
  }, []);
  
  return <UserList users={users} onDelete={handleDelete} />;
};

// ✅ Presentational: pure UI rendering
interface UserListProps {
  users: User[];
  onDelete: (id: string) => void;
}

const UserList: React.FC<UserListProps> = ({ users, onDelete }) => (
  <ul>
    {users.map(user => (
      <UserItem key={user.id} user={user} onDelete={onDelete} />
    ))}
  </ul>
);
```

## Props Design

### Type Definition 🟠

```tsx
// ❌ Bad: Missing or loose types
const Button = (props: any) => { ... };
const Button = ({ onClick, children }) => { ... };

// ✅ Good: Explicit interface with JSDoc
interface ButtonProps {
  /** Button click handler */
  onClick: () => void;
  /** Button content */
  children: React.ReactNode;
  /** Visual variant */
  variant?: 'primary' | 'secondary' | 'danger';
  /** Disabled state */
  disabled?: boolean;
}

const Button: React.FC<ButtonProps> = ({ 
  onClick, 
  children, 
  variant = 'primary',
  disabled = false 
}) => { ... };
```

### Props Spreading 🟡

```tsx
// ❌ Bad: Uncontrolled spreading
const Input = (props: any) => <input {...props} />;

// ✅ Good: Explicit with rest props typed
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

const Input: React.FC<InputProps> = ({ label, error, ...rest }) => (
  <div>
    <label>{label}</label>
    <input {...rest} />
    {error && <span className="error">{error}</span>}
  </div>
);
```

## Hooks Usage

### Dependency Array 🔴

```tsx
// ❌ Bad: Missing dependencies
useEffect(() => {
  fetchUser(userId);
}, []); // userId missing!

// ❌ Bad: Object/array in deps causing infinite loops
useEffect(() => {
  doSomething(options);
}, [options]); // options = {} recreated each render

// ✅ Good: Correct dependencies
useEffect(() => {
  fetchUser(userId);
}, [userId]);

// ✅ Good: Memoize objects/arrays
const options = useMemo(() => ({ page, limit }), [page, limit]);
useEffect(() => {
  doSomething(options);
}, [options]);
```

### Custom Hook Extraction 🟠

Extract when:
- Logic is reused across components
- Logic is complex (> 20 lines)
- Logic involves side effects + state

```tsx
// ❌ Bad: Duplicated logic in components
const ComponentA = () => {
  const [data, setData] = useState();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState();
  
  useEffect(() => {
    setLoading(true);
    fetchData().then(setData).catch(setError).finally(() => setLoading(false));
  }, []);
  // ...
};

// ✅ Good: Extract to custom hook
const useAsyncData = <T,>(fetcher: () => Promise<T>) => {
  const [data, setData] = useState<T>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error>();

  useEffect(() => {
    setLoading(true);
    fetcher()
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [fetcher]);

  return { data, loading, error };
};
```

### Closure Trap 🔴

```tsx
// ❌ Bad: Stale closure
const Counter = () => {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      console.log(count); // Always logs initial value!
      setCount(count + 1); // Always sets to 1!
    }, 1000);
    return () => clearInterval(timer);
  }, []); // count not in deps
};

// ✅ Good: Use functional update
const Counter = () => {
  const [count, setCount] = useState(0);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setCount(prev => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);
};

// ✅ Good: Use ref for latest value
const Counter = () => {
  const [count, setCount] = useState(0);
  const countRef = useRef(count);
  countRef.current = count;
  
  useEffect(() => {
    const timer = setInterval(() => {
      console.log(countRef.current); // Always latest
    }, 1000);
    return () => clearInterval(timer);
  }, []);
};
```

## Accessibility (a11y) 🟠

### Semantic HTML

```tsx
// ❌ Bad: Div soup
<div onClick={handleClick}>Click me</div>
<div className="input" />

// ✅ Good: Semantic elements
<button onClick={handleClick}>Click me</button>
<input type="text" />
```

### ARIA Attributes

```tsx
// ❌ Bad: Missing ARIA
<div className="modal">{content}</div>
<span className="icon-close" onClick={onClose} />

// ✅ Good: Proper ARIA
<div 
  role="dialog" 
  aria-modal="true"
  aria-labelledby="modal-title"
>
  <h2 id="modal-title">Dialog Title</h2>
  {content}
  <button aria-label="Close dialog" onClick={onClose}>
    <CloseIcon aria-hidden="true" />
  </button>
</div>
```

### Keyboard Navigation

```tsx
// ❌ Bad: Mouse-only interaction
<div onClick={handleSelect}>{item}</div>

// ✅ Good: Keyboard accessible
<div
  role="option"
  tabIndex={0}
  onClick={handleSelect}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleSelect();
    }
  }}
  aria-selected={isSelected}
>
  {item}
</div>
```

### Focus Management

```tsx
// ✅ Good: Focus trap in modal
const Modal = ({ isOpen, onClose, children }) => {
  const modalRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (isOpen) {
      const previousFocus = document.activeElement as HTMLElement;
      modalRef.current?.focus();
      
      return () => {
        previousFocus?.focus();
      };
    }
  }, [isOpen]);

  return isOpen ? (
    <div ref={modalRef} tabIndex={-1} role="dialog">
      {children}
    </div>
  ) : null;
};
```

### Color Contrast & Visual

```tsx
// ❌ Bad: Relying only on color
<span className={error ? 'text-red' : 'text-green'}>
  {status}
</span>

// ✅ Good: Color + icon + text
<span className={error ? 'text-red' : 'text-green'}>
  {error ? <ErrorIcon aria-hidden /> : <CheckIcon aria-hidden />}
  {error ? 'Error: ' : 'Success: '}{status}
</span>
```

## Conditional Rendering 🟡

```tsx
// ❌ Bad: Complex ternary chains
{isLoading ? <Loader /> : error ? <Error /> : data ? <Content /> : <Empty />}

// ✅ Good: Early returns or extracted logic
const renderContent = () => {
  if (isLoading) return <Loader />;
  if (error) return <Error error={error} />;
  if (!data) return <Empty />;
  return <Content data={data} />;
};

return <div>{renderContent()}</div>;
```

## Style Handling 🟡

```tsx
// ❌ Bad: Inline conditional classes
<div className={`btn ${primary ? 'btn-primary' : ''} ${disabled ? 'btn-disabled' : ''}`}>

// ✅ Good: Use clsx/tailwind-merge
import { cn } from '@/lib/utils'; // cn = clsx + tailwind-merge

<div className={cn(
  'btn',
  primary && 'btn-primary',
  disabled && 'btn-disabled'
)}>
```
