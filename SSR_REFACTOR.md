# SSR Refactor Documentation

This document describes the Server-Side Rendering (SSR) refactor that was implemented to improve performance and follow Next.js best practices.

## Overview

The application was refactored from a client-side only architecture to a hybrid SSR approach, where:

- **Server Components** handle data fetching and initial rendering
- **Client Components** handle interactivity and user interactions
- **Authentication** moved from client-side (Zustand + localStorage) to server-side (httpOnly cookies)

## Key Changes

### 1. Authentication System

**Before:**

- JWT tokens stored in `localStorage` via Zustand
- Client-side auth checks using `useAuthStore()`
- Tokens sent via Authorization header to tRPC

**After:**

- JWT tokens stored in httpOnly cookies (more secure)
- Server-side auth checks using `getUserId()` from cookies
- Cookies automatically sent with requests

**Files:**

- `src/lib/auth-server.ts` - Server-side auth utilities
- `src/lib/auth-cookies.ts` - Client-side cookie management (unused, kept for reference)
- `src/app/api/auth/set-token/route.ts` - API route to set auth cookie
- `src/app/api/auth/clear-token/route.ts` - API route to clear auth cookie
- `src/server/context.ts` - Updated to read from cookies
- `src/server/routers/auth.ts` - Updated to set cookies on login/signup

### 2. Page Architecture

All pages were converted to Server Components with client components for interactivity:

#### Leagues Page

- **Server Component**: `src/app/leagues/page.tsx` - Fetches leagues from DB
- **Client Component**: `src/app/leagues/leagues-client.tsx` - Handles subscription clicks

#### Subscriptions Page

- **Server Component**: `src/app/subscriptions/page.tsx` - Fetches user subscriptions
- **Client Component**: `src/app/subscriptions/subscriptions-client.tsx` - Handles cancellation

#### Matches Page

- **Server Component**: `src/app/matches/page.tsx` - Fetches matches based on search params
- **Client Component**: `src/app/matches/matches-client.tsx` - Handles filtering and navigation

#### Match Detail Page

- **Server Component**: `src/app/matches/[matchId]/page.tsx` - Fetches match data
- **Client Component**: `src/app/matches/[matchId]/match-detail-client.tsx` - Displays match info and betting recommendations

#### Standings Page

- **Server Component**: `src/app/standings/[leagueId]/page.tsx` - Fetches standings
- **Client Component**: `src/app/standings/[leagueId]/standings-client.tsx` - Displays table

#### Subscribe Page

- **Server Component**: `src/app/subscribe/[leagueId]/page.tsx` - Fetches league data
- **Client Component**: `src/app/subscribe/[leagueId]/subscribe-client.tsx` - Handles checkout

### 3. Data Fetching

**New Server-Side Utilities:**

- `src/lib/data-server.ts` - Server-side data fetching functions
  - `getMatchesByLeague()` - Fetch itematches for a league
  - `getMatchById()` - Fetch match with teams and stats
  - `getLeagueStandings()` - Calculate and fetch standings

**Benefits:**

- Direct database access (faster than tRPC)
- Data available on initial page load (better SEO, faster perceived performance)
- Reduced client-side JavaScript bundle size

### 4. Navigation

**Before:**

- Client component checking `useAuthStore()` for token

**After:**

- Server component (`src/components/navigation.tsx`) checking `getUserId()`
- Client component (`src/components/navigation-client.tsx`) for interactivity

### 5. Removed Code

- `src/stores/auth-store.ts` - Removed (replaced with cookie-based auth)
- Zustand usage for auth - Removed (still used for language preference)

## Architecture Patterns

### Server Component Pattern

```typescript
// Server Component (page.tsx)
export default async function MyPage() {
  const userId = await getUserId();
  if (!userId) redirect('/');
  
  const data = await fetchDataFromDB(userId);
  return <MyClientComponent data={data} />;
}
```

### Client Component Pattern

```typescript
// Client Component (component-client.tsx)
'use client';

export function MyClientComponent({ data }: { data: DataType }) {
  const { t } = useTranslations();
  // Interactive logic here
  return <div>{/* UI */}</div>;
}
```

## Benefits

1. **Performance**
   - Faster initial page loads (data fetched on server)
   - Reduced client-side JavaScript
   - Better SEO (content available on initial HTML)

2. **Security**
   - httpOnly cookies prevent XSS attacks
   - Server-side auth checks are more secure

3. **Developer Experience**
   - Clear separation between server and client code
   - Type-safe data fetching
   - Better error handling

## Migration Notes

### For Developers

1. **Auth Checks**: Use `getUserId()` in server components, not `useAuthStore()`
2. **Data Fetching**: Use `data-server.ts` functions in server components
3. **Interactivity**: Create client components for user interactions
4. **tRPC**: Still used for mutations and client-side updates

### Breaking Changes

- `useAuthStore()` no longer exists - auth is handled server-side
- Pages are now async server components
- Some data fetching moved from tRPC to direct DB calls

## Future Improvements

1. **Language Preference**: Move from Zustand to cookies for SSR compatibility
2. **Caching**: Implement React Server Components caching strategies
3. **Streaming**: Use Suspense boundaries for progressive rendering
4. **Optimistic Updates**: Improve client-side mutation handling
