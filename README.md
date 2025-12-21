# Myoro Arbihawk

Sports analysis application for soccer leagues with subscription-based access,
real-time match statistics, and AI-powered betting recommendations.

## Architecture

### What is tRPC?

**tRPC is optional but recommended.** It provides:

- **Type Safety**: Your frontend automatically knows the exact types from your backend
- **No Code Generation**: Unlike GraphQL, no schema files or codegen needed
- **Autocomplete**: `trpc.auth.signup()` gives you full autocomplete and type checking
- **Shared Types**: Define types once in your backend, use everywhere

**Without tRPC**, you'd use regular REST APIs:

```typescript
// Without tRPC - manual types, no autocomplete
const response = await fetch('/api/auth/signup', {
  method: 'POST',
  body: JSON.stringify({ email, password })
});
const data = await response.json(); // What's in data? 🤷
```

**With tRPC**:

```typescript
// With tRPC - full types, autocomplete, compile-time errors
const result = await trpc.auth.signup.mutate({ email, password });
// TypeScript knows: result.token, result.user.id, etc.
```

### How Next.js Works (Frontend + Backend)

Next.js is both a frontend and backend framework in one:

**Frontend (React Components):**

- `src/app/page.tsx` → Renders in the browser
- Uses `'use client'` directive for interactivity
- Calls backend via tRPC

**Backend (API Routes):**

- `src/app/api/trpc/[trpc]/route.ts` → Runs on server only
- Handles HTTP requests, database queries, authentication
- No `'use client'` = server-side code

**File-Based Routing:**

- `src/app/page.tsx` → `/` (homepage)
- `src/app/about/page.tsx` → `/about`
- `src/app/api/trpc/[trpc]/route.ts` → `/api/trpc/*` (API endpoint)

### Request Flow

```markdown
1. User visits / (homepage)
   ↓
2. Next.js serves src/app/page.tsx (React component)
   ↓
3. User clicks "Sign Up"
   ↓
4. Frontend calls: trpc.auth.signup.mutate({ email, password })
   ↓
5. Request goes to: /api/trpc/auth.signup
   ↓
6. Next.js API route handler runs: src/app/api/trpc/[trpc]/route.ts
   ↓
7. tRPC router processes: src/server/routers/auth.ts
   ↓
8. Backend code runs:
   - Validates input (Zod schema)
   - Checks database (Drizzle ORM)
   - Hashes password (bcrypt)
   - Creates JWT token
   ↓
9. Response sent back to frontend
   ↓
10. React component updates with result
```

### Project Structure

```markdown
myoro-arbihawk/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Frontend: Login page (React)
│   │   ├── layout.tsx             # Frontend: Root layout
│   │   ├── leagues/              # League browsing
│   │   ├── matches/               # Match listings and details
│   │   ├── subscriptions/         # Subscription management
│   │   └── api/
│   │       ├── trpc/              # tRPC API endpoint
│   │       ├── sync/              # Data sync job
│   │       └── webhooks/          # Stripe webhooks
│   ├── components/
│   │   ├── ui/                    # shadcn/ui components
│   │   ├── match-card.tsx         # Match display component
│   │   └── betting-recommendation.tsx
│   ├── server/
│   │   ├── trpc.ts                # Backend: tRPC setup
│   │   ├── context.ts             # Backend: Auth context
│   │   └── routers/               # tRPC routers
│   │       ├── _app.ts            # Main router
│   │       ├── auth.ts            # Authentication
│   │       ├── leagues.ts         # League data
│   │       ├── matches.ts         # Match data
│   │       ├── subscriptions.ts  # Subscription management
│   │       ├── stripe.ts         # Stripe checkout
│   │       ├── stats.ts          # Statistics
│   │       └── betting.ts        # Betting recommendations
│   ├── lib/
│   │   ├── auth.ts                # Password hashing, user CRUD
│   │   ├── jwt.ts                 # Token creation/verification
│   │   ├── stripe.ts              # Stripe integration
│   │   ├── api-football.ts        # RapidAPI client
│   │   ├── betting-engine.ts      # Recommendation algorithm
│   │   ├── cache.ts               # Caching utilities
│   │   └── seed-dev.ts            # Auto-seeding for dev
│   ├── db/
│   │   ├── schema.ts              # Database: Table definitions
│   │   ├── index.ts               # Database: Connection
│   │   └── seed.ts                # Database seeding
│   ├── stores/                    # Zustand state management
│   ├── hooks/                     # React hooks
│   └── utils/
│       └── trpc.ts                # Frontend: tRPC client setup
├── .github/workflows/
│   └── ci.yml                     # CI/CD pipeline
├── package.json                   # Dependencies and scripts
└── drizzle.config.ts             # Database migrations config
```

### Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **API**: tRPC (type-safe API layer)
- **Database**: PostgreSQL + Drizzle ORM
- **Auth**: JWT + bcrypt
- **Payments**: Stripe (subscriptions)
- **Sports Data**: RapidAPI (API-Football)
- **Styling**: Tailwind CSS + shadcn/ui
- **State**: React Query (via tRPC) + Zustand
- **i18n**: Custom typed localization (20 languages)
- **Package Manager**: Bun
- **Linting**: ESLint + Prettier
- **CI/CD**: GitHub Actions

## Setup

### Quick Start (Recommended - Docker)

1. **Install dependencies:**

```bash
bun install
```

2. **Start PostgreSQL with Docker:**

```bash
bun run docker:up
```

This starts PostgreSQL in a Docker container with default credentials:
- User: `postgres`
- Password: `postgres`
- Database: `myoro_arbihawk`
- Port: `5432`

3. **Set up environment variables:**

Create a `.env` file in the project root:

```bash
# Database (matches Docker Compose defaults)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/myoro_arbihawk

# JWT Secret (generate with: openssl rand -base64 32)
JWT_SECRET=your-secret-key-here

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...

# API-Football (RapidAPI)
RAPIDAPI_KEY=your-rapidapi-key-here
RAPIDAPI_HOST=api-football-v1.p.rapidapi.com

# Application URL
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Sync Job Token
SYNC_JOB_TOKEN=your-sync-job-token-here
```

4. **Run complete setup (creates DB, runs migrations, seeds data):**

```bash
bun run setup
```

This automatically:
- Creates the database if it doesn't exist
- Runs migrations to create tables
- Seeds test users

5. **Start development server:**

```bash
bun run dev
```

Visit `http://localhost:3000`

### Manual Setup (Without Docker)

If you prefer to use a local PostgreSQL installation:

1. **Install dependencies:**

```bash
bun install
```

2. **Set up environment variables:**

Create a `.env` file with your PostgreSQL credentials:

```bash
DATABASE_URL=postgresql://username:password@localhost:5432/myoro_arbihawk
# ... other env vars
```

3. **Create database and run migrations:**

```bash
bun run setup
```

Or manually:
```bash
bun run db:setup    # Creates database
bun run db:migrate  # Runs migrations
bun run db:seed     # Seeds test data
```

4. **Start development server:**

```bash
bun run dev
```

### Test Users

The seed script creates two test users:

- `admin@example.com` / `admin123`
- `user@example.com` / `user123`

**Note:** Seeding is safe to run multiple times - it checks for existing users first.

## Development

### Application Commands

- `bun run dev` - Start Next.js dev server (auto-seeds database)
- `bun run build` - Build for production
- `bun run start` - Start production server
- `bun run lint` - Run ESLint
- `bun run lint:fix` - Fix linting issues and format code
- `bun run format` - Format code with Prettier
- `bun run format:check` - Check if code is formatted

### Database Commands

- `bun run setup` - Complete setup (creates DB, migrates, seeds)
- `bun run db:setup` - Create database if it doesn't exist
- `bun run db:generate` - Generate database migration files
- `bun run db:migrate` - Apply migrations to database
- `bun run db:seed` - Manually seed database with test users
- `bun run db:studio` - Open Drizzle Studio (database GUI)

### Docker Commands

- `bun run docker:up` - Start PostgreSQL container
- `bun run docker:down` - Stop PostgreSQL container
- `bun run docker:logs` - View PostgreSQL logs

## Code Quality

### Linting & Formatting

The project uses ESLint and Prettier with the following rules:

- **Semicolons**: Required
- **Line Length**: 80 characters
- **Quotes**: Single quotes
- **Trailing Commas**: ES5 style

Run `bun run lint:fix` to automatically fix most issues.

### CI/CD

GitHub Actions automatically checks:

- Code formatting (Prettier)
- Linting (ESLint)
- Type checking (TypeScript)

The CI pipeline runs on every push and pull request.

## Key Concepts

### tRPC Procedures

- **publicProcedure**: Anyone can call (e.g., `auth.signup`, `auth.login`)
- **protectedProcedure**: Requires valid JWT token (e.g., `matches.getByLeague`)

### Authentication Flow

1. User signs up/logs in → Gets JWT token
2. Token stored in `localStorage` (via Zustand)
3. Token sent in `Authorization: Bearer <token>` header
4. Backend verifies token in `context.ts`
5. Protected routes check `ctx.userId`

### Database

- **Schema**: Defined in `src/db/schema.ts`
- **Migrations**: Generated with `drizzle-kit generate`
- **Queries**: Use Drizzle ORM throughout the codebase
- **Seeding**: Automatically runs in development mode

### Database Seeding

The seed script (`src/db/seed.ts`) automatically runs when you start the dev
server. It creates test users for development:

- **<admin@example.com>** / **admin123**
- **<user@example.com>** / **user123**

**How it works:**

1. Checks if users already exist (safe to run multiple times)
2. Hashes passwords using bcrypt
3. Inserts users into the database
4. Logs progress to console

**Auto-seeding:**

- Runs automatically when `bun run dev` starts
- Only runs in development mode (not in production)
- Fails gracefully if database isn't available

### Subscriptions

- Users can subscribe to individual leagues
- Stripe handles payment processing
- Webhooks update subscription status automatically
- Subscription required to access match data and betting recommendations

### Sports Data

- Data synced from RapidAPI (API-Football)
- Background sync job at `/api/sync`
- Caching to minimize API calls
- Real-time match statistics

### Betting Recommendations

- AI-powered algorithm analyzes historical data
- Confidence scores (0-100%) for each recommendation
- Recommendations include: Win/Draw, Over/Under goals
- Only available to subscribed users
