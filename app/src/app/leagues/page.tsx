import { db } from '@/db';
import { leagues } from '@/db/schema';
import { eq } from 'drizzle-orm';
import { getUserId } from '@/lib/auth-server';
import { LeaguesClient } from './leagues-client';

/**
 * Leagues browsing page (Server Component).
 *
 * Fetches leagues on the server and passes to client component for interactivity.
 */
export default async function LeaguesPage() {
  const userId = await getUserId();

  // Fetch leagues directly from database
  const leaguesData = await db
    .select()
    .from(leagues)
    .where(eq(leagues.isActive, true));

  return (
    <LeaguesClient leagues={leaguesData} isAuthenticated={userId !== null} />
  );
}
