# Performance Checklist

Guidelines for reviewing React application performance: rendering, memory, and bundle optimization.

## Rendering Performance

### Unnecessary Re-renders 🔴

```tsx
// ❌ Bad: New object/array on every render
const Parent = () => {
  return <Child style={{ color: 'red' }} items={[1, 2, 3]} />;
  // style and items are new references every render!
};

// ✅ Good: Stable references
const style = { color: 'red' };
const items = [1, 2, 3];

const Parent = () => {
  return <Child style={style} items={items} />;
};

// ✅ Good: useMemo for dynamic values
const Parent = ({ color }) => {
  const style = useMemo(() => ({ color }), [color]);
  return <Child style={style} />;
};
```

### memo Usage 🟠

```tsx
// ❌ Bad: memo without stable props
const Child = memo(({ onClick }) => { ... });

const Parent = () => {
  // onClick is new function every render - memo is useless!
  return <Child onClick={() => doSomething()} />;
};

// ✅ Good: memo with useCallback
const Child = memo(({ onClick }) => { ... });

const Parent = () => {
  const onClick = useCallback(() => doSomething(), []);
  return <Child onClick={onClick} />;
};

// ❌ Bad: memo on component that always re-renders anyway
const AlwaysChanging = memo(({ timestamp }) => {
  return <div>{timestamp}</div>; // timestamp changes every second
});

// ✅ Good: Only memo components with stable props
const ExpensiveList = memo(({ items }) => {
  return items.map(item => <ExpensiveItem key={item.id} item={item} />);
});
```

### useMemo/useCallback Overuse 🟡

```tsx
// ❌ Bad: Premature optimization
const Component = () => {
  // Don't memoize cheap operations
  const doubled = useMemo(() => count * 2, [count]);
  const handleClick = useCallback(() => setCount(c => c + 1), []);
  
  return <button onClick={handleClick}>{doubled}</button>;
};

// ✅ Good: Only memoize when necessary
const Component = () => {
  const doubled = count * 2; // Cheap, no memo needed
  
  return (
    <button onClick={() => setCount(c => c + 1)}>
      {doubled}
    </button>
  );
};

// ✅ Good: Memoize expensive computations
const Component = ({ items }) => {
  const sortedItems = useMemo(
    () => [...items].sort((a, b) => complexSort(a, b)),
    [items]
  );
  
  return <List items={sortedItems} />;
};
```

### List Rendering 🔴

```tsx
// ❌ Bad: Index as key with dynamic list
{items.map((item, index) => (
  <Item key={index} item={item} /> // Bug when items reorder!
))}

// ✅ Good: Stable unique key
{items.map((item) => (
  <Item key={item.id} item={item} />
))}

// ❌ Bad: Rendering huge lists
{allItems.map(item => <Item key={item.id} item={item} />)}
// 10,000 items = 10,000 DOM nodes!

// ✅ Good: Virtualization for large lists
import { useVirtualizer } from '@tanstack/react-virtual';

const VirtualList = ({ items }) => {
  const parentRef = useRef<HTMLDivElement>(null);
  
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
  });
  
  return (
    <div ref={parentRef} style={{ height: 400, overflow: 'auto' }}>
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <Item
            key={items[virtualItem.index].id}
            item={items[virtualItem.index]}
            style={{
              position: 'absolute',
              top: virtualItem.start,
              height: virtualItem.size,
            }}
          />
        ))}
      </div>
    </div>
  );
};
```

## Memory Management

### Event Listener Cleanup 🔴

```tsx
// ❌ Bad: Memory leak
useEffect(() => {
  window.addEventListener('resize', handleResize);
  // Missing cleanup!
}, []);

// ✅ Good: Proper cleanup
useEffect(() => {
  window.addEventListener('resize', handleResize);
  return () => window.removeEventListener('resize', handleResize);
}, []);

// ✅ Better: Use ahooks
import { useEventListener } from 'ahooks';

useEventListener('resize', handleResize);
```

### Timer Cleanup 🔴

```tsx
// ❌ Bad: Memory leak
useEffect(() => {
  setInterval(() => {
    updateData();
  }, 1000);
}, []);

// ✅ Good: Clear timer
useEffect(() => {
  const timer = setInterval(() => {
    updateData();
  }, 1000);
  
  return () => clearInterval(timer);
}, []);
```

### Subscription Cleanup 🔴

```tsx
// ❌ Bad: Memory leak with RxJS
useEffect(() => {
  data$.subscribe(setData);
}, []);

// ✅ Good: Unsubscribe
useEffect(() => {
  const sub = data$.subscribe(setData);
  return () => sub.unsubscribe();
}, []);
```

### AbortController for Fetch 🟠

```tsx
// ❌ Bad: Race condition, state update after unmount
useEffect(() => {
  fetchData().then(setData);
}, [id]);

// ✅ Good: Abort on cleanup
useEffect(() => {
  const controller = new AbortController();
  
  fetchData(id, { signal: controller.signal })
    .then(setData)
    .catch((err) => {
      if (err.name !== 'AbortError') {
        setError(err);
      }
    });
  
  return () => controller.abort();
}, [id]);
```

## Bundle Optimization

### Code Splitting 🟠

```tsx
// ❌ Bad: Import everything upfront
import { HeavyChart } from './HeavyChart';
import { HeavyEditor } from './HeavyEditor';

// ✅ Good: Lazy load heavy components
const HeavyChart = lazy(() => import('./HeavyChart'));
const HeavyEditor = lazy(() => import('./HeavyEditor'));

const App = () => (
  <Suspense fallback={<Loading />}>
    {showChart && <HeavyChart />}
    {showEditor && <HeavyEditor />}
  </Suspense>
);
```

### Dynamic Import 🟠

```tsx
// ❌ Bad: Import large library at top level
import moment from 'moment'; // 300KB!
import lodash from 'lodash'; // 70KB!

// ✅ Good: Dynamic import when needed
const formatDate = async (date: Date) => {
  const { format } = await import('date-fns');
  return format(date, 'yyyy-MM-dd');
};

// ✅ Good: Import specific functions
import { debounce } from 'lodash-es'; // Tree-shakeable
// or
import debounce from 'lodash/debounce'; // Only 2KB
```

### Tree Shaking Friendly 🟡

```tsx
// ❌ Bad: Barrel exports break tree shaking
// utils/index.ts
export * from './string';
export * from './number';
export * from './date';

// ✅ Good: Direct imports
import { formatDate } from '@/utils/date';
import { formatNumber } from '@/utils/number';
```

### Image Optimization 🟡

```tsx
// ❌ Bad: Unoptimized images
<img src="/huge-image.png" />

// ✅ Good: Optimized with next/image (Next.js)
import Image from 'next/image';
<Image src="/image.png" width={800} height={600} alt="Description" />

// ✅ Good: Lazy loading (CSR)
<img src="/image.png" loading="lazy" alt="Description" />

// ✅ Good: Responsive images
<img
  src="/image.png"
  srcSet="/image-400.png 400w, /image-800.png 800w"
  sizes="(max-width: 600px) 400px, 800px"
  alt="Description"
/>
```

## Style Performance

### TailwindCSS 🟡

```tsx
// ❌ Bad: Dynamic class names (can't be purged)
<div className={`text-${color}-500`} />

// ✅ Good: Explicit class names
<div className={color === 'red' ? 'text-red-500' : 'text-blue-500'} />

// ✅ Good: Use CSS variables for dynamic values
<div 
  className="text-[var(--dynamic-color)]"
  style={{ '--dynamic-color': color } as React.CSSProperties}
/>
```

### CSS-in-JS 🟠

```tsx
// ❌ Bad: Creating styled component inside render
const Component = () => {
  // New component created every render!
  const StyledDiv = styled.div`
    color: ${props => props.color};
  `;
  
  return <StyledDiv color="red" />;
};

// ✅ Good: Define outside component
const StyledDiv = styled.div<{ color: string }>`
  color: ${props => props.color};
`;

const Component = () => {
  return <StyledDiv color="red" />;
};
```

## Performance Metrics 💡

### Core Web Vitals Targets

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| LCP (Largest Contentful Paint) | ≤ 2.5s | ≤ 4s | > 4s |
| INP (Interaction to Next Paint) | ≤ 200ms | ≤ 500ms | > 500ms |
| CLS (Cumulative Layout Shift) | ≤ 0.1 | ≤ 0.25 | > 0.25 |

### React DevTools Profiler

Check for:
- Components rendering > 16ms (60fps threshold)
- Unnecessary re-renders (same props, same output)
- Render cascades (parent → many children)

### Bundle Size Budgets

| Category | Budget |
|----------|--------|
| Initial JS | < 200KB gzipped |
| Per-route chunk | < 50KB gzipped |
| Total CSS | < 50KB gzipped |
| Largest dependency | < 50KB gzipped |
