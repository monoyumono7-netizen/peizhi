# Next.js SSR Checklist

Guidelines for reviewing Next.js 15 App Router applications with SSR and Turbopack.

## Server vs Client Components

### Default to Server Components 🟠

```tsx
// ✅ Good: Server Component (default in App Router)
// app/users/page.tsx
async function UsersPage() {
  const users = await db.users.findMany(); // Direct DB access
  
  return (
    <ul>
      {users.map(user => <li key={user.id}>{user.name}</li>)}
    </ul>
  );
}

export default UsersPage;
```

### Client Component Boundaries 🔴

```tsx
// ❌ Bad: Entire page as Client Component
'use client';

export default function Page() {
  const [count, setCount] = useState(0);
  // Now EVERYTHING is client-rendered
  return <LargeComponent />;
}

// ✅ Good: Minimal Client Component boundary
// app/page.tsx (Server Component)
export default function Page() {
  return (
    <div>
      <ServerContent />
      <Counter /> {/* Only this is client */}
    </div>
  );
}

// components/Counter.tsx
'use client';
export function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

### 'use client' Placement 🔴

```tsx
// ❌ Bad: 'use client' in shared component used by Server Components
// components/Button.tsx
'use client'; // This forces all parents to be Client Components!

export function Button({ children }) {
  return <button>{children}</button>;
}

// ✅ Good: Only add 'use client' when actually needed
// components/Button.tsx
export function Button({ children, onClick }) {
  return <button onClick={onClick}>{children}</button>;
}

// components/InteractiveButton.tsx
'use client';
export function InteractiveButton() {
  const [clicked, setClicked] = useState(false);
  return <Button onClick={() => setClicked(true)}>{clicked ? 'Clicked!' : 'Click me'}</Button>;
}
```

## Data Fetching

### Server-Side Data Fetching 🟠

```tsx
// ❌ Bad: useEffect for initial data
'use client';
export default function Page() {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    fetch('/api/data').then(r => r.json()).then(setData);
  }, []);
  
  return <div>{data?.title}</div>;
}

// ✅ Good: Server Component with async
// app/page.tsx
async function Page() {
  const data = await fetch('https://api.example.com/data', {
    next: { revalidate: 60 } // ISR: revalidate every 60s
  }).then(r => r.json());
  
  return <div>{data.title}</div>;
}

export default Page;
```

### Parallel Data Fetching 🟠

```tsx
// ❌ Bad: Sequential fetches (waterfall)
async function Page() {
  const user = await getUser();
  const posts = await getPosts(user.id); // Waits for user
  const comments = await getComments(posts[0].id); // Waits for posts
}

// ✅ Good: Parallel fetches
async function Page() {
  const userPromise = getUser();
  const postsPromise = getPosts();
  
  const [user, posts] = await Promise.all([userPromise, postsPromise]);
  
  return <Content user={user} posts={posts} />;
}
```

### Streaming with Suspense 🟡

```tsx
// ✅ Good: Stream slow data
import { Suspense } from 'react';

async function Page() {
  return (
    <div>
      <Header /> {/* Renders immediately */}
      <Suspense fallback={<PostsSkeleton />}>
        <SlowPosts /> {/* Streams when ready */}
      </Suspense>
      <Suspense fallback={<CommentsSkeleton />}>
        <SlowComments /> {/* Streams independently */}
      </Suspense>
    </div>
  );
}

async function SlowPosts() {
  const posts = await getSlowPosts(); // 2s delay
  return <PostsList posts={posts} />;
}
```

## Hydration Issues

### Hydration Mismatch 🔴

```tsx
// ❌ Bad: Different content on server vs client
function Component() {
  return <div>{typeof window !== 'undefined' ? 'Client' : 'Server'}</div>;
  // Hydration error! Server renders "Server", client expects "Client"
}

// ❌ Bad: Using Date/Math.random without suppression
function Component() {
  return <div>{new Date().toISOString()}</div>; // Different on server vs client!
}

// ✅ Good: Use useEffect for client-only values
function Component() {
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);
  
  if (!mounted) return <div>Loading...</div>;
  
  return <div>{new Date().toISOString()}</div>;
}

// ✅ Good: Suppress hydration warning when intentional
function Component() {
  return (
    <time suppressHydrationWarning>
      {new Date().toISOString()}
    </time>
  );
}
```

### Window/Document Access 🔴

```tsx
// ❌ Bad: Accessing window at module level
const width = window.innerWidth; // Error on server!

// ❌ Bad: Accessing window in render
function Component() {
  const width = window.innerWidth; // Error on server!
  return <div style={{ width }} />;
}

// ✅ Good: Access in useEffect
function Component() {
  const [width, setWidth] = useState(0);
  
  useEffect(() => {
    setWidth(window.innerWidth);
    
    const handleResize = () => setWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  return <div style={{ width: width || '100%' }} />;
}

// ✅ Good: Dynamic import for browser-only libraries
const Editor = dynamic(() => import('./Editor'), { 
  ssr: false,
  loading: () => <EditorSkeleton />
});
```

### localStorage/sessionStorage 🔴

```tsx
// ❌ Bad: Direct access
const theme = localStorage.getItem('theme'); // Error on server!

// ✅ Good: Safe access with fallback
function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    if (typeof window === 'undefined') return initialValue;
    
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });
  
  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);
  
  return [value, setValue] as const;
}
```

## App Router Patterns

### Route Groups 🟡

```
app/
├── (marketing)/      # No URL impact
│   ├── about/
│   └── contact/
├── (dashboard)/      # Separate layout
│   ├── settings/
│   └── profile/
└── layout.tsx        # Root layout
```

### Parallel Routes 🟡

```tsx
// app/layout.tsx
export default function Layout({
  children,
  modal,
}: {
  children: React.ReactNode;
  modal: React.ReactNode;
}) {
  return (
    <>
      {children}
      {modal}
    </>
  );
}

// app/@modal/photo/[id]/page.tsx
export default function PhotoModal({ params }: { params: { id: string } }) {
  return <Modal><Photo id={params.id} /></Modal>;
}
```

### Loading & Error States 🟠

```tsx
// app/posts/loading.tsx - Automatic loading UI
export default function Loading() {
  return <PostsSkeleton />;
}

// app/posts/error.tsx - Error boundary
'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={reset}>Try again</button>
    </div>
  );
}

// app/posts/not-found.tsx - 404 handling
export default function NotFound() {
  return <div>Post not found</div>;
}
```

## Metadata & SEO 🟡

```tsx
// app/posts/[id]/page.tsx
import { Metadata } from 'next';

// Static metadata
export const metadata: Metadata = {
  title: 'Posts',
};

// Dynamic metadata
export async function generateMetadata({ 
  params 
}: { 
  params: { id: string } 
}): Promise<Metadata> {
  const post = await getPost(params.id);
  
  return {
    title: post.title,
    description: post.excerpt,
    openGraph: {
      title: post.title,
      images: [post.coverImage],
    },
  };
}
```

## Server Actions 🟠

```tsx
// ❌ Bad: API route for simple mutations
// app/api/posts/route.ts
export async function POST(req: Request) {
  const data = await req.json();
  await db.posts.create({ data });
  return Response.json({ success: true });
}

// ✅ Good: Server Action
// app/posts/actions.ts
'use server';

import { revalidatePath } from 'next/cache';

export async function createPost(formData: FormData) {
  const title = formData.get('title') as string;
  
  await db.posts.create({ data: { title } });
  
  revalidatePath('/posts');
}

// app/posts/new/page.tsx
import { createPost } from './actions';

export default function NewPost() {
  return (
    <form action={createPost}>
      <input name="title" required />
      <button type="submit">Create</button>
    </form>
  );
}
```

## Internationalization (next-intl) 🟡

```tsx
// middleware.ts
import createMiddleware from 'next-intl/middleware';

export default createMiddleware({
  locales: ['en', 'zh'],
  defaultLocale: 'en',
});

// app/[locale]/layout.tsx
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';

export default async function LocaleLayout({
  children,
  params: { locale },
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  const messages = await getMessages();
  
  return (
    <NextIntlClientProvider messages={messages}>
      {children}
    </NextIntlClientProvider>
  );
}
```

## Turbopack Considerations 💡

### Supported Features

- Fast Refresh
- TypeScript
- CSS Modules
- PostCSS
- Tailwind CSS
- next/image
- next/font

### Known Limitations (as of Next.js 15)

- Some webpack plugins not supported
- Custom webpack config may not work
- Check `next dev --turbo` compatibility

```json
// package.json
{
  "scripts": {
    "dev": "next dev --turbo",
    "build": "next build"
  }
}
```
