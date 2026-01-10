import { eq } from 'drizzle-orm';
import { db } from '../index';
import { leagues } from '../schema';

/**
 * Seed data for leagues.
 */
const leagueData = [
  {
    name: 'Premier League',
    country: 'England',
    apiLeagueId: 39,
    isActive: true,
  },
  {
    name: 'La Liga',
    country: 'Spain',
    apiLeagueId: 140,
    isActive: true,
  },
  {
    name: 'Bundesliga',
    country: 'Germany',
    apiLeagueId: 78,
    isActive: true,
  },
  {
    name: 'Serie A',
    country: 'Italy',
    apiLeagueId: 135,
    isActive: true,
  },
];

/**
 * Seeds leagues table with test data.
 *
 * @returns Array of league IDs
 */
export async function seedLeagues(): Promise<string[]> {
  console.log('[seed]: \n🏆 Creating leagues...');
  const leagueIds: string[] = [];

  for (const leagueInfo of leagueData) {
    const existing = await db
      .select()
      .from(leagues)
      .where(eq(leagues.apiLeagueId, leagueInfo.apiLeagueId))
      .limit(1);

    if (existing.length > 0) {
      const existingLeague = existing[0];
      if (existingLeague) {
        console.log(`[seed]: ⏭️  League ${leagueInfo.name} already exists`);
        leagueIds.push(existingLeague.id);
        continue;
      }
    }

    const [league] = await db.insert(leagues).values(leagueInfo).returning();
    if (!league) {
      throw new Error(`Failed to create league: ${leagueInfo.name}`);
    }
    leagueIds.push(league.id);
    console.log(`[seed]: ✅ Created league: ${leagueInfo.name}`);
  }

  return leagueIds;
}
