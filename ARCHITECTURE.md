# MyoroArbihawk Architecture

Cross-platform monorepo with shared screens and business logic across web, desktop, and mobile.

## Structure

```
packages/
├── backend/   # Elysia + tRPC + Prisma
├── ui/        # Tamagui design system
├── i18n/      # Localization (19 languages)
├── shared/    # Screens, hooks, stores, services
├── web/       # Vite + React (browser)
├── desktop/   # Vite + React + Electron
└── mobile/    # Expo + React Native
```

## Package Dependency Graph

```
backend (standalone)
    │
    ▼ (types only)
shared ◄── ui
    │       │
    ▼       │
  i18n ◄────┘
    │
    ▼
web / desktop / mobile (consume all above)
```

## Packages

### `@repo/backend`
Elysia server with tRPC and Prisma.

### `@repo/ui`
Tamagui components: Button, Text, Card, Input, VStack, HStack, Center.

### `@repo/i18n`
Type-safe localization for 19 languages. Add strings to `en.json`, then all locale files.

### `@repo/shared`
- **Screens**: `CounterScreen`
- **Hooks**: `useCounter`
- **Stores**: `useCounterStore` (Zustand)
- **Services**: `trpc`, `httpClient`
- **Providers**: `AppProvider`

### `@repo/web`
Vite + React for browser. Port 5173.

### `@repo/desktop`
Vite + React + Electron for desktop. Port 5174.

### `@repo/mobile`
Expo + React Native for iOS/Android.

## Commands

```bash
# Install
bun install

# Database
bun run db:generate
bun run db:push

# Development
bun run dev:backend   # Start backend
bun run dev:web       # Start web
bun run dev:desktop   # Start desktop (Electron)
bun run dev:mobile    # Start mobile (Expo)

# Build
bun run build:web
bun run build:desktop
bun run build:mobile
```

## Adding Features

**New screen**: Add to `packages/shared/src/screens/`, export from index.

**New component**: Add to `packages/ui/src/components/`, export from index.

**New API endpoint**: Add procedure to `packages/backend/src/trpc/index.ts`.

**New translations**: Add keys to all locale files in `packages/i18n/src/locales/`.

