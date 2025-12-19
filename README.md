# Myoro Arbihawk

Sports analysis application with Next.js frontend and Elysia backend.

## Setup

1. Install dependencies:
```bash
bun install
```

2. Set up PostgreSQL database and create `.env` file:
```bash
cp .env.example .env
# Edit .env with your DATABASE_URL and JWT_SECRET
```

3. Generate and run migrations:
```bash
cd packages/server
bun run db:generate
bun run db:migrate
```

4. Start development servers:
```bash
# From root
bun run dev

# Or separately:
bun run dev:server  # Backend on :3001
bun run dev:web     # Frontend on :3000
```

## Project Structure

```
myoro-arbihawk/
├── packages/
│   ├── web/          # Next.js frontend
│   └── server/       # Elysia backend with tRPC
└── package.json      # Workspace root
```

## Tech Stack

- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS, tRPC
- **Backend**: Elysia, tRPC, Drizzle ORM, PostgreSQL
- **Auth**: JWT, bcrypt
- **Package Manager**: Bun

