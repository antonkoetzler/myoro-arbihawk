import { redirect } from 'next/navigation';
import { getUserId } from '@/lib/auth-server';
import { getLeagueStandings } from '@/lib/data-server';
import { db } from '@/db';
import { leagues } from '@/db/schema';
import { eq } from 'drizzle-orm';
import { StandingsClient } from './standings-client';
import { z } from 'zod';

const standingsParamsSchema = z.object({
  leagueId: z.string().uuid(),
});

/**
 * League standings page (Server Component).
 *
 * Fetches league and standings data on the server.
 */
export default async function StandingsPage({
  params,
}: {
  params: { leagueId: string };
}) {
  const userId = await getUserId();

  if (!userId) {
    redirect('/');
  }

  const parsed = standingsParamsSchema.safeParse(params);
  if (!parsed.success) {
    redirect('/');
  }

  const [league] = await db
    .select()
    .from(leagues)
    .where(eq(leagues.id, parsed.data.leagueId))
    .limit(1);

  if (!league) {
    redirect('/');
  }

  let standings: Awaited<ReturnType<typeof getLeagueStandings>> = [];
  try {
    standings = await getLeagueStandings(userId, parsed.data.leagueId);
  } catch {
    // User doesn't have access
    standings = [];
  }

  return <StandingsClient league={league} standings={standings} />;
}
