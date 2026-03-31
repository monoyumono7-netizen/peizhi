# State Management Checklist

Guidelines for reviewing RxJS + Zustand hybrid state management patterns.

## When to Use What

### Decision Matrix

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| Simple UI state (modal open, form input) | `useState` | Local, no sharing needed |
| Shared UI state across siblings | Zustand | Simple, React-optimized |
| Complex async data streams | RxJS | Powerful operators for streams |
| Real-time data (WebSocket, SSE) | RxJS | Built for reactive streams |
| Global app state (user, theme) | Zustand | Simple global state |
| Cross-component event bus | RxJS Subject | Decoupled communication |
| Server state (API data) | React Query / SWR | Caching, deduplication |

### Anti-Patterns 🔴

```tsx
// ❌ Bad: Using RxJS for simple state
const isModalOpen$ = new BehaviorSubject(false);

// ✅ Good: Use useState or Zustand
const [isModalOpen, setIsModalOpen] = useState(false);
// or
const useModalStore = create((set) => ({
  isOpen: false,
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
}));
```

```tsx
// ❌ Bad: Using Zustand for complex async streams
const useDataStore = create((set) => ({
  data: null,
  fetchData: async () => {
    // Complex retry, debounce, merge logic here...
  },
}));

// ✅ Good: Use RxJS for complex streams
const data$ = fromEvent(socket, 'message').pipe(
  debounceTime(300),
  retry(3),
  map(parseMessage),
  shareReplay(1)
);
```

## RxJS Patterns

### Subscription Cleanup 🔴

```tsx
// ❌ Bad: Memory leak - no cleanup
useEffect(() => {
  data$.subscribe(setData);
}, []);

// ❌ Bad: Memory leak - subscription not stored
useEffect(() => {
  const sub = data$.subscribe(setData);
  // forgot to return cleanup
}, []);

// ✅ Good: Proper cleanup
useEffect(() => {
  const subscription = data$.subscribe(setData);
  return () => subscription.unsubscribe();
}, []);

// ✅ Better: Use takeUntil pattern
useEffect(() => {
  const destroy$ = new Subject<void>();
  
  data$.pipe(takeUntil(destroy$)).subscribe(setData);
  
  return () => {
    destroy$.next();
    destroy$.complete();
  };
}, []);
```

### BehaviorSubject Usage 🟠

```tsx
// ❌ Bad: Exposing BehaviorSubject directly
export const user$ = new BehaviorSubject<User | null>(null);
// Anyone can call user$.next() - no control

// ✅ Good: Encapsulate with getter/setter
class UserState {
  private _user$ = new BehaviorSubject<User | null>(null);
  
  get user$(): Observable<User | null> {
    return this._user$.asObservable();
  }
  
  get currentUser(): User | null {
    return this._user$.getValue();
  }
  
  setUser(user: User | null): void {
    this._user$.next(user);
  }
}

export const userState = new UserState();
```

### Error Handling 🔴

```tsx
// ❌ Bad: Unhandled errors kill the stream
data$.subscribe(setData);

// ✅ Good: Handle errors
data$.subscribe({
  next: setData,
  error: (err) => {
    console.error('Stream error:', err);
    setError(err);
  },
});

// ✅ Better: Recover from errors
data$.pipe(
  catchError((err) => {
    console.error('Recovering from:', err);
    return of(fallbackValue);
  })
).subscribe(setData);
```

### Operator Selection 🟡

```tsx
// ❌ Bad: Wrong operator for the job
// Using mergeMap when order matters
searchInput$.pipe(
  mergeMap(query => searchAPI(query)) // Results may arrive out of order!
);

// ✅ Good: Use switchMap for search (cancel previous)
searchInput$.pipe(
  debounceTime(300),
  distinctUntilChanged(),
  switchMap(query => searchAPI(query))
);

// ✅ Good: Use concatMap when order matters
queue$.pipe(
  concatMap(task => processTask(task))
);

// ✅ Good: Use exhaustMap to ignore while busy
submitButton$.pipe(
  exhaustMap(() => submitForm())
);
```

## Zustand Patterns

### Store Design 🟠

```tsx
// ❌ Bad: Monolithic store
const useStore = create((set) => ({
  user: null,
  posts: [],
  comments: [],
  notifications: [],
  theme: 'light',
  // ... 50 more properties
}));

// ✅ Good: Split by domain
const useUserStore = create<UserStore>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  logout: () => set({ user: null }),
}));

const useThemeStore = create<ThemeStore>((set) => ({
  theme: 'light',
  toggleTheme: () => set((s) => ({ 
    theme: s.theme === 'light' ? 'dark' : 'light' 
  })),
}));
```

### Selector Optimization 🟠

```tsx
// ❌ Bad: Selecting entire store
const Component = () => {
  const store = useUserStore(); // Re-renders on ANY change
  return <div>{store.user?.name}</div>;
};

// ✅ Good: Select only what you need
const Component = () => {
  const userName = useUserStore((s) => s.user?.name);
  return <div>{userName}</div>;
};

// ✅ Good: Use shallow for object selection
import { shallow } from 'zustand/shallow';

const Component = () => {
  const { name, email } = useUserStore(
    (s) => ({ name: s.user?.name, email: s.user?.email }),
    shallow
  );
};
```

### Async Actions 🟡

```tsx
// ❌ Bad: Async logic in component
const Component = () => {
  const setUser = useUserStore((s) => s.setUser);
  
  useEffect(() => {
    fetchUser().then(setUser);
  }, []);
};

// ✅ Good: Async action in store
const useUserStore = create<UserStore>((set, get) => ({
  user: null,
  loading: false,
  error: null,
  
  fetchUser: async () => {
    set({ loading: true, error: null });
    try {
      const user = await fetchUserAPI();
      set({ user, loading: false });
    } catch (error) {
      set({ error: error as Error, loading: false });
    }
  },
}));
```

## Hybrid Patterns

### RxJS → Zustand Bridge 🟠

```tsx
// ✅ Good: Sync RxJS stream to Zustand
const useDataStore = create<DataStore>((set) => ({
  data: null,
  error: null,
  
  // Initialize subscription
  init: () => {
    const subscription = data$.subscribe({
      next: (data) => set({ data, error: null }),
      error: (error) => set({ error }),
    });
    
    return () => subscription.unsubscribe();
  },
}));

// In app initialization
useEffect(() => {
  const cleanup = useDataStore.getState().init();
  return cleanup;
}, []);
```

### Zustand → RxJS Bridge 🟡

```tsx
// ✅ Good: Create observable from Zustand
import { create } from 'zustand';
import { BehaviorSubject } from 'rxjs';

const useCountStore = create<CountStore>((set) => ({
  count: 0,
  increment: () => set((s) => ({ count: s.count + 1 })),
}));

// Create observable from store
const count$ = new BehaviorSubject(useCountStore.getState().count);
useCountStore.subscribe((state) => count$.next(state.count));

// Now count$ can be used with RxJS operators
count$.pipe(
  debounceTime(500),
  distinctUntilChanged()
).subscribe(saveToServer);
```

## State Colocation 🟡

### Principle: State should live close to where it's used

```tsx
// ❌ Bad: Global state for local concern
const useStore = create((set) => ({
  searchQuery: '', // Only used in SearchBar
}));

// ✅ Good: Local state for local concern
const SearchBar = () => {
  const [query, setQuery] = useState('');
  // ...
};

// ✅ Good: Lift state only when needed
const SearchPage = () => {
  const [query, setQuery] = useState('');
  
  return (
    <>
      <SearchBar value={query} onChange={setQuery} />
      <SearchResults query={query} />
    </>
  );
};
```

## Derived State 🟠

```tsx
// ❌ Bad: Redundant state
const useStore = create((set) => ({
  items: [],
  itemCount: 0, // Redundant! Can be derived
  setItems: (items) => set({ items, itemCount: items.length }),
}));

// ✅ Good: Derive in selector
const useStore = create((set) => ({
  items: [],
  setItems: (items) => set({ items }),
}));

// Usage
const itemCount = useStore((s) => s.items.length);

// ✅ Good: Memoized derived state
const useItemStats = () => {
  const items = useStore((s) => s.items);
  
  return useMemo(() => ({
    count: items.length,
    total: items.reduce((sum, i) => sum + i.price, 0),
    average: items.length ? items.reduce((sum, i) => sum + i.price, 0) / items.length : 0,
  }), [items]);
};
```
