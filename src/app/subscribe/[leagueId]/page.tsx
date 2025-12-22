import { redirect } from 'next/navigation';
import { getUserId } from '@/lib/auth-server';
import { db } from '@/db';
import { leagues } from '@/db/schema';
import { eq } from 'drizzle-orm';
import { SubscribeClient } from './subscribe-client';
import { LeagueNotFound } from './league-not-found';
import { z } from 'zod';

const subscribeParamsSchema = z.object({
  leagueId: z.string().uuid(),
});

/**
 * Subscription checkout page (Server Component).
 *
 * Fetches league data on the server.
 */
export default async function SubscribePage({
  params,
}: {
  params: { leagueId: string };
}) {
  const userId = await getUserId();

  if (!userId) {
    redirect('/');
  }

  const parsed = subscribeParamsSchema.safeParse(params);
  if (!parsed.success) {
    redirect('/');
  }

  const [league] = await db
    .select()
    .from(leagues)
    .where(eq(leagues.id, parsed.data.leagueId))
    .limit(1);

  if (!league) {
    return <LeagueNotFound />;
  }

  return <SubscribeClient league={league} />;
}
