/**
 * Database setup script.
 *
 * Automatically creates the database if it doesn't exist,
 * then runs migrations and seeds.
 */

import postgres from 'postgres';
import { execSync } from 'child_process';

/**
 * Checks if Docker container is running.
 */
function isDockerContainerRunning(containerName: string): boolean {
  try {
    const output = execSync(
      `docker ps --filter "name=${containerName}" --format "{{.Status}}"`,
      { encoding: 'utf-8', stdio: 'pipe' }
    );
    return output.trim().includes('Up');
  } catch {
    return false;
  }
}

/**
 * Tests PostgreSQL connection with a simple query.
 */
async function testConnection(
  connectionUrl: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const testClient = postgres(connectionUrl, {
      max: 1,
      connect_timeout: 5,
    });
    await testClient`SELECT 1`;
    await testClient.end();
    return { success: true };
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : String(error);
    return { success: false, error: errorMessage };
  }
}

/**
 * Extracts database connection info from DATABASE_URL.
 */
function parseDatabaseUrl(url: string) {
  try {
    const parsed = new URL(url);
    return {
      host: parsed.hostname,
      port: parseInt(parsed.port || '5432', 10),
      user: parsed.username,
      password: parsed.password,
      database: parsed.pathname.slice(1), // Remove leading '/'
    };
  } catch {
    return null;
  }
}

/**
 * Creates the database if it doesn't exist.
 */
async function ensureDatabase() {
  const databaseUrl =
    process.env.DATABASE_URL ||
    'postgresql://postgres:postgres@localhost:5432/myoro_arbihawk';

  const parsed = parseDatabaseUrl(databaseUrl);
  if (!parsed) {
    console.error('[ensureDatabase]: ❌ Invalid DATABASE_URL format');
    process.exit(1);
  }

  // Check if using Docker and verify container is running
  if (parsed.host === 'localhost' || parsed.host === '127.0.0.1') {
    const containerRunning = isDockerContainerRunning('myoro-arbihawk-db');
    if (!containerRunning) {
      console.error('[ensureDatabase]: ❌ Docker container is not running');
      console.error('[ensureDatabase]: Start it with: bun run docker:up');
      console.error('[ensureDatabase]: Or check container status: docker ps -a | grep myoro');
      process.exit(1);
    }
  }

  // Connect to postgres database (default database that always exists)
  const adminUrl = databaseUrl.replace(`/${parsed.database}`, '/postgres');

  // Test connection
  console.log('[ensureDatabase]: 🔌 Testing PostgreSQL connection...');
  const connectionResult = await testConnection(adminUrl);
  if (!connectionResult.success) {
    console.error('[ensureDatabase]: \n❌ Cannot connect to PostgreSQL');
    console.error(`[ensureDatabase]: Connection URL: ${adminUrl.replace(/:[^:@]+@/, ':****@')}`);
    if (connectionResult.error) {
      console.error(`[ensureDatabase]: Error: ${connectionResult.error}`);
    }
    console.error('[ensureDatabase]: \nTroubleshooting:');
    console.error('[ensureDatabase]: 1. Check if PostgreSQL is running:');
    console.error('[ensureDatabase]:    - Docker: bun run docker:up');
    console.error('[ensureDatabase]:    - Local: Check service status');
    console.error('[ensureDatabase]: 2. Check container logs: docker logs myoro-arbihawk-db');
    console.error('[ensureDatabase]: 3. Verify DATABASE_URL in .env file');
    console.error('[ensureDatabase]: 4. Wait a few seconds if container just started');
    process.exit(1);
  }
  console.log('[ensureDatabase]: ✓ Connected to PostgreSQL\n');

  const adminClient = postgres(adminUrl, { max: 1 });

  try {
    // Check if database exists
    const result = await adminClient`
      SELECT 1 FROM pg_database WHERE datname = ${parsed.database}
    `;

    if (result.length === 0) {
      console.log(`[ensureDatabase]: 📦 Creating database: ${parsed.database}...`);
      await adminClient.unsafe(`CREATE DATABASE ${parsed.database}`);
      console.log('[ensureDatabase]: ✅ Database created successfully');
    } else {
      console.log(`[ensureDatabase]: ✓ Database ${parsed.database} already exists`);
    }
  } catch (error) {
    console.error('[ensureDatabase]: ❌ Failed to create database:', error);
    process.exit(1);
  } finally {
    await adminClient.end();
  }
}

/**
 * Main setup function.
 */
async function setup() {
  console.log('[setup]: 🚀 Setting up database...\n');

  try {
    await ensureDatabase();
    console.log('');
    process.exit(0);
  } catch (error) {
    console.error('[setup]: ❌ Setup failed:', error);
    process.exit(1);
  }
}

// Run if executed directly (Bun)
if (import.meta.main) {
  setup();
}

export { ensureDatabase };

