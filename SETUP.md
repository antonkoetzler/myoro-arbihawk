# Setup Guide

This guide will help you get the application running quickly.

## Prerequisites

- [Bun](https://bun.sh) installed
- [Docker](https://www.docker.com) (optional, but recommended)

## Quick Start (Recommended)

### 1. Install Dependencies

```bash
bun install
```

### 2. Start PostgreSQL with Docker

```bash
bun run docker:up
```

This starts PostgreSQL in a Docker container. The default credentials are:

- **User**: `postgres`
- **Password**: `postgres`
- **Database**: `myoro_arbihawk`
- **Port**: `5432`

### 3. Create Environment File

Copy the example environment file:

```bash
cp .env.example .env
```

Or create `.env` manually with:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/myoro_arbihawk
JWT_SECRET=your-secret-key-here
# ... other variables
```

### 4. Run Complete Setup

This will:

- Create the database (if it doesn't exist)
- Run migrations to create tables
- Seed test users

```bash
bun run setup
```

### 5. Start Development Server

```bash
bun run dev
```

Visit `http://localhost:3000`

## Manual Setup (Without Docker)

If you have PostgreSQL installed locally:

1. **Install dependencies:**

   ```bash
   bun install
   ```

2. **Create `.env` file** with your PostgreSQL credentials:

   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/myoro_arbihawk
   ```

3. **Run setup:**

   ```bash
   bun run setup
   ```

4. **Start dev server:**

   ```bash
   bun run dev
   ```

## Troubleshooting

### Database Connection Errors

**Error: `password authentication failed`**

- Check your `DATABASE_URL` in `.env`
- For Docker: Use `postgresql://postgres:postgres@localhost:5432/myoro_arbihawk`
- Verify PostgreSQL is running: `bun run docker:logs`

**Error: `database does not exist`**

- Run: `bun run db:setup` to create the database

**Error: `relation does not exist`**

- Run: `bun run db:migrate` to create tables

### Docker Issues

**Container won't start:**

```bash
# Check if port 5432 is already in use
# Stop existing PostgreSQL if needed
bun run docker:down
bun run docker:up
```

**View logs:**

```bash
bun run docker:logs
```

## Test Users

After seeding, you can log in with:

- `admin@example.com` / `admin123`
- `user@example.com` / `user123`

## Available Commands

See `README.md` for a complete list of commands.
