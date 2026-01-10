import { redirect } from 'next/navigation';
import { getUserId } from '@/lib/auth-server';
import { getMatchById } from '@/lib/data-server';
import { MatchDetailClient } from './match-detail-client';
import { MatchNotFound } from './match-not-found';
import { z } from 'zod';

const matchDetailParamsSchema = z.object({
  matchId: z.string().uuid(),
});

/**
 * Match detail page (Server Component).
 *
 * Fetches match data on the server.
 */
export default async function MatchDetailPage({
  params,
}: {
  params: { matchId: string };
}) {
  const userId = await getUserId();

  if (!userId) {
    redirect('/');
  }

  const parsed = matchDetailParamsSchema.safeParse(params);
  if (!parsed.success) {
    redirect('/');
  }

  const matchData = await getMatchById(userId, parsed.data.matchId);

  if (!matchData) {
    return <MatchNotFound />;
  }

  return <MatchDetailClient matchData={matchData} />;
}
