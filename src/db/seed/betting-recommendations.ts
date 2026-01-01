import { eq } from 'drizzle-orm';
import { db } from '../index';
import { matches, bettingRecommendations } from '../schema';

/**
 * Seeds betting recommendations for matches.
 */
export async function seedBettingRecommendations(): Promise<void> {
  console.log('[seed]: \n🎲 Creating betting recommendations...');
  const matchesForRecommendations = await db.select().from(matches).limit(10);

  for (const match of matchesForRecommendations) {
    const existing = await db
      .select()
      .from(bettingRecommendations)
      .where(eq(bettingRecommendations.matchId, match.id))
      .limit(1);

    if (existing.length > 0) {
      continue;
    }

    const recommendations = [
      {
        betType: 'win' as const,
        recommendation: 'Home Win',
        confidencePercentage: 65 + Math.floor(Math.random() * 20),
      },
      {
        betType: 'over' as const,
        recommendation: 'Over 2.5 Goals',
        confidencePercentage: 70 + Math.floor(Math.random() * 15),
      },
    ];

    for (const rec of recommendations) {
      await db.insert(bettingRecommendations).values({
        matchId: match.id,
        betType: rec.betType,
        recommendation: rec.recommendation,
        confidencePercentage: rec.confidencePercentage,
      });
    }
    console.log(
      `[seed]: ✅ Created betting recommendations for match ${match.id.slice(0, 8)}...`
    );
  }
}
