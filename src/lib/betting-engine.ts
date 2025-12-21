import { db } from '@/db';
import { matches, bettingRecommendations } from '@/db/schema';
import { eq, desc } from 'drizzle-orm';

/**
 * Betting recommendation engine.
 *
 * Analyzes historical match data to generate betting recommendations
 * with confidence scores.
 */

/**
 * Calculates betting recommendations for a match.
 *
 * @param matchId - Match ID
 * @returns Array of betting recommendations
 */
export async function calculateBettingRecommendations(matchId: string) {
  const [match] = await db
    .select()
    .from(matches)
    .where(eq(matches.id, matchId))
    .limit(1);

  if (!match) {
    throw new Error('Match not found');
  }

  // Get recent matches for both teams
  const homeTeamRecentMatches = await db
    .select()
    .from(matches)
    .where(
      and(
        eq(matches.leagueId, match.leagueId)
        // Match where team is home or away
        // Simplified - in production, use OR condition
      )
    )
    .orderBy(desc(matches.date))
    .limit(5);

  const awayTeamRecentMatches = await db
    .select()
    .from(matches)
    .where(
      and(
        eq(matches.leagueId, match.leagueId)
        // Match where team is home or away
      )
    )
    .orderBy(desc(matches.date))
    .limit(5);

  // Calculate team form (simplified)
  const homeForm = calculateTeamForm(homeTeamRecentMatches, match.homeTeamId);
  const awayForm = calculateTeamForm(awayTeamRecentMatches, match.awayTeamId);

  // Calculate recommendations
  const recommendations = [];

  // Win/Draw recommendation
  const homeWinProbability = calculateWinProbability(homeForm, awayForm, true);
  const drawProbability = 0.3; // Simplified
  const awayWinProbability = calculateWinProbability(awayForm, homeForm, false);

  if (homeWinProbability > 0.5) {
    recommendations.push({
      betType: 'win' as const,
      recommendation: 'Home Win',
      confidencePercentage: Math.round(homeWinProbability * 100),
    });
  } else if (awayWinProbability > 0.5) {
    recommendations.push({
      betType: 'win' as const,
      recommendation: 'Away Win',
      confidencePercentage: Math.round(awayWinProbability * 100),
    });
  } else {
    recommendations.push({
      betType: 'draw' as const,
      recommendation: 'Draw',
      confidencePercentage: Math.round(drawProbability * 100),
    });
  }

  // Over/Under recommendation (simplified)
  const avgGoals = (homeForm.avgGoalsScored + awayForm.avgGoalsScored) / 2;
  if (avgGoals > 2.5) {
    recommendations.push({
      betType: 'over' as const,
      recommendation: 'Over 2.5 Goals',
      confidencePercentage: Math.min(Math.round((avgGoals / 3) * 100), 90),
    });
  } else {
    recommendations.push({
      betType: 'under' as const,
      recommendation: 'Under 2.5 Goals',
      confidencePercentage: Math.min(
        Math.round(((3 - avgGoals) / 3) * 100),
        90
      ),
    });
  }

  // Save recommendations to database
  for (const rec of recommendations) {
    await db.insert(bettingRecommendations).values({
      matchId: match.id,
      betType: rec.betType,
      recommendation: rec.recommendation,
      confidencePercentage: rec.confidencePercentage,
    });
  }

  return recommendations;
}

/**
 * Calculates team form from recent matches.
 */
function calculateTeamForm(
  recentMatches: Array<{
    homeTeamId: string;
    awayTeamId: string;
    homeScore: number | null;
    awayScore: number | null;
  }>,
  teamId: string
) {
  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goalsScored = 0;
  let goalsConceded = 0;

  for (const match of recentMatches) {
    const isHome = match.homeTeamId === teamId;
    const teamScore = isHome ? match.homeScore : match.awayScore;
    const opponentScore = isHome ? match.awayScore : match.homeScore;

    if (teamScore === null || opponentScore === null) {
      continue;
    }

    goalsScored += teamScore;
    goalsConceded += opponentScore;

    if (teamScore > opponentScore) {
      wins++;
    } else if (teamScore === opponentScore) {
      draws++;
    } else {
      losses++;
    }
  }

  const totalMatches = recentMatches.length || 1;

  return {
    wins,
    draws,
    losses,
    avgGoalsScored: goalsScored / totalMatches,
    avgGoalsConceded: goalsConceded / totalMatches,
    winRate: wins / totalMatches,
  };
}

/**
 * Calculates win probability for a team.
 */
function calculateWinProbability(
  teamForm: ReturnType<typeof calculateTeamForm>,
  opponentForm: ReturnType<typeof calculateTeamForm>,
  isHome: boolean
): number {
  // Simplified probability calculation
  const homeAdvantage = isHome ? 0.1 : 0;
  const formAdvantage = teamForm.winRate - opponentForm.winRate;
  const goalAdvantage =
    (teamForm.avgGoalsScored - opponentForm.avgGoalsConceded) / 3;

  const probability =
    0.33 + homeAdvantage + formAdvantage * 0.3 + goalAdvantage * 0.2;
  return Math.max(0.1, Math.min(0.9, probability));
}
