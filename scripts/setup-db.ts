/**
 * Database setup script.
 *
 * Automatically creates the database if it doesn't exist,
 * then runs migrations and seeds.
 */

import postgres from 'postgres';

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
    process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/myoro_arbihawk';

  const parsed = parseDatabaseUrl(databaseUrl);
  if (!parsed) {
    console.error('❌ Invalid DATABASE_URL format');
    process.exit(1);
  }

  // Connect to postgres database (default database that always exists)
  const adminUrl = databaseUrl.replace(`/${parsed.database}`, '/postgres');
  const adminClient = postgres(adminUrl, { max: 1 });

  try {
    // Check if database exists
    const result = await adminClient`
      SELECT 1 FROM pg_database WHERE datname = ${parsed.database}
    `;

    if (result.length === 0) {
      console.log(`📦 Creating database: ${parsed.database}...`);
      await adminClient.unsafe(`CREATE DATABASE ${parsed.database}`);
      console.log('✅ Database created successfully');
    } else {
      console.log(`✓ Database ${parsed.database} already exists`);
    }
  } catch (error) {
    console.error('❌ Failed to create database:', error);
    process.exit(1);
  } finally {
    await adminClient.end();
  }
}

/**
 * Main setup function.
 */
async function setup() {
  console.log('🚀 Setting up database...\n');

  try {
    await ensureDatabase();
    console.log('');
    process.exit(0);
  } catch (error) {
    console.error('❌ Setup failed:', error);
    process.exit(1);
  }
}

// Run if executed directly (Bun)
if (import.meta.main) {
  setup();
}

export { ensureDatabase };

