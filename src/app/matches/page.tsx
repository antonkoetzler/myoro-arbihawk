import { redirect } from 'next/navigation';
import { getUserId } from '@/lib/auth-server';
import { getUserSubscriptions } from '@/lib/subscription-check';
import { getMatchesByLeague } from '@/lib/data-server';
import { MatchesClient } from './matches-client';

/**
 * Matches listing page (Server Component).
 *
 * Fetches user subscriptions and matches on the server.
 */
export default async function MatchesPage({
  searchParams,
}: {
  searchParams: { leagueId?: string; status?: string };
}) {
  const userId = await getUserId();

  if (!userId) {
    redirect('/');
  }

  const subscriptions = await getUserSubscriptions(userId);

  if (!subscriptions || subscriptions.length === 0) {
    return (
      <div className='container mx-auto py-8'>
        <MatchesClient
          subscriptions={[]}
          matches={[]}
          selectedLeagueId={null}
          statusFilter={undefined}
        />
      </div>
    );
  }

  const selectedLeagueId =
    searchParams.leagueId || subscriptions[0]?.league.id || null;
  const statusFilter = searchParams.status as 'scheduled' | 'live' | undefined;

  let matches = [];
  if (selectedLeagueId) {
    try {
      // Only fetch live and scheduled matches (finished are excluded)
      matches = await getMatchesByLeague(
        userId,
        selectedLeagueId,
        statusFilter
      );
    } catch {
      // User doesn't have access or error occurred
      matches = [];
    }
  }

  return (
    <MatchesClient
      subscriptions={subscriptions}
      matches={matches}
      selectedLeagueId={selectedLeagueId}
      statusFilter={statusFilter}
    />
  );
}
