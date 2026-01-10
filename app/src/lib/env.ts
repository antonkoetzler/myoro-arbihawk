import { z } from 'zod';

/**
 * Environment variable schema.
 *
 * Validates all environment variables at startup.
 * Throws error if required vars are missing or invalid.
 */
const envSchema = z.object({
  // Database
  DATABASE_URL: z
    .string()
    .url()
    .optional()
    .default('postgresql://postgres:postgres@localhost:5432/myoro_arbihawk'),

  // JWT
  JWT_SECRET: z
    .string()
    .min(32)
    .optional()
    .default('dev-secret-key-change-this-in-production-min-32-chars-required'),

  // Stripe
  STRIPE_SECRET_KEY: z.string().startsWith('sk_').optional(),
  STRIPE_PUBLISHABLE_KEY: z.string().startsWith('pk_').optional(),
  STRIPE_WEBHOOK_SECRET: z.string().startsWith('whsec_').optional(),
  STRIPE_PRICE_ID: z.string().startsWith('price_').optional(),

  // API-Football (RapidAPI)
  RAPIDAPI_KEY: z.string().min(1).optional(),
  RAPIDAPI_HOST: z
    .string()
    .optional()
    .default('api-football-v1.p.rapidapi.com'),

  // Application
  NEXT_PUBLIC_APP_URL: z
    .string()
    .url()
    .optional()
    .default('http://localhost:3000'),

  // Sync Job
  SYNC_JOB_TOKEN: z.string().min(1).optional(),

  // Node Environment
  NODE_ENV: z
    .enum(['development', 'production', 'test'])
    .optional()
    .default('development'),
});

/**
 * Validated and typed environment variables.
 *
 * Access env vars through this object instead of process.env directly.
 * All values are validated and typed at startup.
 *
 * @example
 * ```typescript
 * import { env } from '@/lib/env';
 * const dbUrl = env.DATABASE_URL; // Typed as string
 * ```
 */
export const env = envSchema.parse({
  DATABASE_URL: process.env.DATABASE_URL,
  JWT_SECRET: process.env.JWT_SECRET,
  STRIPE_SECRET_KEY: process.env.STRIPE_SECRET_KEY,
  STRIPE_PUBLISHABLE_KEY: process.env.STRIPE_PUBLISHABLE_KEY,
  STRIPE_WEBHOOK_SECRET: process.env.STRIPE_WEBHOOK_SECRET,
  STRIPE_PRICE_ID: process.env.STRIPE_PRICE_ID,
  RAPIDAPI_KEY: process.env.RAPIDAPI_KEY,
  RAPIDAPI_HOST: process.env.RAPIDAPI_HOST,
  NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
  SYNC_JOB_TOKEN: process.env.SYNC_JOB_TOKEN,
  NODE_ENV: process.env.NODE_ENV,
});

/**
 * Validates optional environment variables and logs warnings in development.
 *
 * Called automatically when this module is imported.
 * Helps developers identify missing optional configuration.
 */
if (env.NODE_ENV === 'development') {
  const missingOptionalVars: string[] = [];

  if (!process.env.RAPIDAPI_KEY) {
    missingOptionalVars.push('RAPIDAPI_KEY (for API-Football integration)');
  }

  if (!process.env.STRIPE_SECRET_KEY) {
    missingOptionalVars.push('STRIPE_SECRET_KEY (for payments)');
  }

  if (!process.env.STRIPE_PUBLISHABLE_KEY) {
    missingOptionalVars.push('STRIPE_PUBLISHABLE_KEY (for payments)');
  }

  if (!process.env.STRIPE_WEBHOOK_SECRET) {
    missingOptionalVars.push(
      'STRIPE_WEBHOOK_SECRET (for webhook verification)'
    );
  }

  if (!process.env.STRIPE_PRICE_ID) {
    missingOptionalVars.push('STRIPE_PRICE_ID (for subscription pricing)');
  }

  if (!process.env.SYNC_JOB_TOKEN) {
    missingOptionalVars.push('SYNC_JOB_TOKEN (for background sync jobs)');
  }

  if (missingOptionalVars.length > 0) {
    // Use console.warn directly here since logger might not be initialized yet
    // and this is a one-time startup message
    console.warn(
      '[env] ⚠️  Missing optional environment variables (features may be limited):\n' +
        missingOptionalVars.map((v) => `  - ${v}`).join('\n') +
        '\n\nThese are optional but may be needed for full functionality.'
    );
  }
}
