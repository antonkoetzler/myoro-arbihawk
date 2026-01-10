import { eq } from 'drizzle-orm';
import { db } from '../index';
import { teams } from '../schema';

/**
 * Team data organized by league index.
 */
const teamData = [
  // Premier League teams
  [
    { name: 'Arsenal', apiTeamId: 42 },
    { name: 'Chelsea', apiTeamId: 49 },
    { name: 'Liverpool', apiTeamId: 40 },
    { name: 'Manchester City', apiTeamId: 50 },
    { name: 'Manchester United', apiTeamId: 33 },
    { name: 'Tottenham', apiTeamId: 47 },
  ],
  // La Liga teams
  [
    { name: 'Barcelona', apiTeamId: 541 },
    { name: 'Real Madrid', apiTeamId: 541 },
    { name: 'Atletico Madrid', apiTeamId: 530 },
    { name: 'Sevilla', apiTeamId: 541 },
    { name: 'Valencia', apiTeamId: 532 },
    { name: 'Villarreal', apiTeamId: 533 },
  ],
  // Bundesliga teams
  [
    { name: 'Bayern Munich', apiTeamId: 157 },
    { name: 'Borussia Dortmund', apiTeamId: 165 },
    { name: 'RB Leipzig', apiTeamId: 173 },
    { name: 'Bayer Leverkusen', apiTeamId: 168 },
    { name: 'Eintracht Frankfurt', apiTeamId: 169 },
    { name: 'Wolfsburg', apiTeamId: 161 },
  ],
  // Serie A teams
  [
    { name: 'AC Milan', apiTeamId: 489 },
    { name: 'Inter Milan', apiTeamId: 108 },
    { name: 'Juventus', apiTeamId: 109 },
    { name: 'Napoli', apiTeamId: 492 },
    { name: 'Roma', apiTeamId: 497 },
    { name: 'Lazio', apiTeamId: 487 },
  ],
];

/**
 * Seeds teams table with test data.
 *
 * @param leagueIds - Array of league IDs corresponding to teamData indices
 * @returns Record mapping team name to team ID
 */
export async function seedTeams(
  leagueIds: string[]
): Promise<Record<string, string>> {
  console.log('[seed]: \n⚽ Creating teams...');
  const teamIds: Record<string, string> = {};

  for (let leagueIndex = 0; leagueIndex < teamData.length; leagueIndex++) {
    const leagueId = leagueIds[leagueIndex];
    if (!leagueId) {
      continue;
    }
    const leagueTeams = teamData[leagueIndex];
    if (!leagueTeams) {
      continue;
    }

    for (const teamInfo of leagueTeams) {
      const existing = await db
        .select()
        .from(teams)
        .where(eq(teams.apiTeamId, teamInfo.apiTeamId))
        .limit(1);

      if (existing.length > 0) {
        const existingTeam = existing[0];
        if (existingTeam) {
          teamIds[teamInfo.name] = existingTeam.id;
        }
        continue;
      }

      const [team] = await db
        .insert(teams)
        .values({
          leagueId,
          name: teamInfo.name,
          apiTeamId: teamInfo.apiTeamId,
        })
        .returning();
      if (!team) {
        throw new Error(`Failed to create team: ${teamInfo.name}`);
      }
      teamIds[teamInfo.name] = team.id;
      console.log(`[seed]: ✅ Created team: ${teamInfo.name}`);
    }
  }

  return teamIds;
}
