import { eq } from 'drizzle-orm';
import { db } from '../index';
import { matches, matchStats } from '../schema';

/**
 * Seeds match stats for finished matches.
 */
export async function seedMatchStats(): Promise<void> {
  console.log('[seed]: \n📊 Creating match stats...');
  const finishedMatches = await db
    .select()
    .from(matches)
    .where(eq(matches.status, 'finished'))
    .limit(20);

  for (const match of finishedMatches) {
    const existing = await db
      .select()
      .from(matchStats)
      .where(eq(matchStats.matchId, match.id))
      .limit(1);

    if (existing.length > 0) {
      continue;
    }

    await db.insert(matchStats).values({
      matchId: match.id,
      homePossession: 55 + Math.floor(Math.random() * 10),
      awayPossession: 45 - Math.floor(Math.random() * 10),
      homeShots: 10 + Math.floor(Math.random() * 10),
      awayShots: 8 + Math.floor(Math.random() * 8),
      homeShotsOnTarget: 5 + Math.floor(Math.random() * 5),
      awayShotsOnTarget: 4 + Math.floor(Math.random() * 4),
      homeCorners: 5 + Math.floor(Math.random() * 5),
      awayCorners: 3 + Math.floor(Math.random() * 5),
      homeFouls: 10 + Math.floor(Math.random() * 5),
      awayFouls: 12 + Math.floor(Math.random() * 5),
      homeYellowCards: Math.floor(Math.random() * 3),
      awayYellowCards: Math.floor(Math.random() * 3),
      homeRedCards: Math.floor(Math.random() * 2),
      awayRedCards: Math.floor(Math.random() * 2),
    });
    console.log(
      `[seed]: ✅ Created stats for match ${match.id.slice(0, 8)}...`
    );
  }
}
