import { eq, and } from 'drizzle-orm';
import { db } from './index';
import {
  users,
  leagues,
  teams,
  matches,
  subscriptions,
  matchStats,
  bettingRecommendations,
} from './schema';
import { hashPassword } from '../lib/auth';

/**
 * Seeds the database with comprehensive test data.
 *
 * Creates:
 * - Test users (admin@example.com, user@example.com)
 * - Multiple leagues (Premier League, La Liga, Bundesliga, Serie A)
 * - Teams for each league
 * - Matches (scheduled, live, finished) for each league
 * - Subscriptions for admin@example.com to all leagues
 * - Match stats for finished matches
 * - Betting recommendations for some matches
 *
 * Safe to run multiple times - checks for existing data first.
 */
export async function seed() {
  console.log('[seed]: 🌱 Seeding database...');

  // 1. Create users
  console.log('[seed]: \n📝 Creating users...');
  const testUsers = [
    { email: 'admin@example.com', password: 'admin123' },
    { email: 'user@example.com', password: 'user123' },
  ];

  const userIds: Record<string, string> = {};

  for (const { email, password } of testUsers) {
    const existing = await db
      .select()
      .from(users)
      .where(eq(users.email, email))
      .limit(1);

    if (existing.length > 0) {
      console.log(`[seed]: ⏭️  User ${email} already exists`);
      userIds[email] = existing[0].id;
      continue;
    }

    const passwordHash = await hashPassword(password);
    const [user] = await db
      .insert(users)
      .values({ email, passwordHash })
      .returning();
    userIds[email] = user.id;
    console.log(`[seed]: ✅ Created user: ${email} / ${password}`);
  }

  const adminUserId = userIds['admin@example.com'];

  // 2. Create leagues
  console.log('[seed]: \n🏆 Creating leagues...');
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

  const leagueIds: string[] = [];

  for (const leagueInfo of leagueData) {
    const existing = await db
      .select()
      .from(leagues)
      .where(eq(leagues.apiLeagueId, leagueInfo.apiLeagueId))
      .limit(1);

    if (existing.length > 0) {
      console.log(`[seed]: ⏭️  League ${leagueInfo.name} already exists`);
      leagueIds.push(existing[0].id);
      continue;
    }

    const [league] = await db.insert(leagues).values(leagueInfo).returning();
    leagueIds.push(league.id);
    console.log(`[seed]: ✅ Created league: ${leagueInfo.name}`);
  }

  // 3. Create teams for each league
  console.log('[seed]: \n⚽ Creating teams...');

  // Premier League teams
  const premierLeagueTeams = [
    { name: 'Arsenal', apiTeamId: 42 },
    { name: 'Chelsea', apiTeamId: 49 },
    { name: 'Liverpool', apiTeamId: 40 },
    { name: 'Manchester City', apiTeamId: 50 },
    { name: 'Manchester United', apiTeamId: 33 },
    { name: 'Tottenham', apiTeamId: 47 },
  ];

  // La Liga teams
  const laLigaTeams = [
    { name: 'Barcelona', apiTeamId: 541 },
    { name: 'Real Madrid', apiTeamId: 541 },
    { name: 'Atletico Madrid', apiTeamId: 530 },
    { name: 'Sevilla', apiTeamId: 541 },
    { name: 'Valencia', apiTeamId: 532 },
    { name: 'Villarreal', apiTeamId: 533 },
  ];

  // Bundesliga teams
  const bundesligaTeams = [
    { name: 'Bayern Munich', apiTeamId: 157 },
    { name: 'Borussia Dortmund', apiTeamId: 165 },
    { name: 'RB Leipzig', apiTeamId: 173 },
    { name: 'Bayer Leverkusen', apiTeamId: 168 },
    { name: 'Eintracht Frankfurt', apiTeamId: 169 },
    { name: 'Wolfsburg', apiTeamId: 161 },
  ];

  // Serie A teams
  const serieATeams = [
    { name: 'AC Milan', apiTeamId: 489 },
    { name: 'Inter Milan', apiTeamId: 108 },
    { name: 'Juventus', apiTeamId: 109 },
    { name: 'Napoli', apiTeamId: 492 },
    { name: 'Roma', apiTeamId: 497 },
    { name: 'Lazio', apiTeamId: 487 },
  ];

  const allTeams = [
    { leagueIndex: 0, teams: premierLeagueTeams },
    { leagueIndex: 1, teams: laLigaTeams },
    { leagueIndex: 2, teams: bundesligaTeams },
    { leagueIndex: 3, teams: serieATeams },
  ];

  const teamIds: Record<string, string> = {};

  for (const { leagueIndex, teams: leagueTeams } of allTeams) {
    const leagueId = leagueIds[leagueIndex];

    for (const teamInfo of leagueTeams) {
      const existing = await db
        .select()
        .from(teams)
        .where(eq(teams.apiTeamId, teamInfo.apiTeamId))
        .limit(1);

      if (existing.length > 0) {
        teamIds[teamInfo.name] = existing[0].id;
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
      teamIds[teamInfo.name] = team.id;
      console.log(`[seed]: ✅ Created team: ${teamInfo.name}`);
    }
  }

  // 4. Create subscriptions for admin user
  console.log('[seed]: \n💳 Creating subscriptions...');
  for (const leagueId of leagueIds) {
    const existing = await db
      .select()
      .from(subscriptions)
      .where(
        and(
          eq(subscriptions.userId, adminUserId),
          eq(subscriptions.leagueId, leagueId)
        )
      )
      .limit(1);

    if (existing.length > 0) {
      console.log(`[seed]: ⏭️  Subscription already exists for league`);
      continue;
    }

    const periodEnd = new Date();
    periodEnd.setMonth(periodEnd.getMonth() + 1);

    await db.insert(subscriptions).values({
      userId: adminUserId,
      leagueId,
      stripeSubscriptionId: `sub_test_${leagueId.slice(0, 8)}`,
      stripeCustomerId: `cus_test_${adminUserId.slice(0, 8)}`,
      status: 'active',
      currentPeriodEnd: periodEnd,
    });
    console.log(`[seed]: ✅ Created subscription for admin user`);
  }

  // 5. Create match stats for finished matches
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

  // 6. Create betting recommendations
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

  console.log('[seed]: \n✨ Seeding complete!');
  console.log('[seed]: \n📋 Summary:');
  console.log(`[seed]:    - Users: ${testUsers.length}`);
  console.log(`[seed]:    - Leagues: ${leagueIds.length}`);
  console.log(`[seed]:    - Teams: ${Object.keys(teamIds).length}`);
  console.log(
    `[seed]:    - Subscriptions: ${leagueIds.length} (for admin@example.com)`
  );
  console.log(
    `[seed]: \n💡 Note: Matches will be fetched from RapidAPI when you navigate to /matches`
  );
  console.log(
    `[seed]: \n🔑 Login credentials:\n   - admin@example.com / admin123\n   - user@example.com / user123`
  );
}

/**
 * Runs seed and properly handles errors.
 */
async function runSeed() {
  try {
    await seed();
    process.exit(0);
  } catch (error: unknown) {
    console.error('[runSeed]: \n❌ Seed failed:', error);

    if (error && typeof error === 'object' && 'code' in error) {
      const errorCode = String(error.code);
      const errorMessage =
        'message' in error && typeof error.message === 'string'
          ? error.message
          : '';

      if (errorCode === 'ECONNREFUSED') {
        console.error('[runSeed]: \n❌ Database connection refused!');
        console.error(
          '[runSeed]: PostgreSQL is not running or not accessible.\n'
        );
        console.error('[runSeed]: To fix:');
        console.error('[runSeed]: 1. If using Docker: docker-compose up -d');
        console.error('[runSeed]: 2. If using local PostgreSQL:');
        console.error('[runSeed]:    - Windows: Start PostgreSQL service');
        console.error('[runSeed]:    - macOS: brew services start postgresql');
        console.error(
          '[runSeed]:    - Linux: sudo systemctl start postgresql\n'
        );
      } else if (
        errorCode === '28P01' ||
        errorMessage.includes('password authentication failed')
      ) {
        console.error('[runSeed]: \n❌ Database authentication failed!');
        console.error('[runSeed]: Invalid username or password.\n');
        console.error('[runSeed]: To fix:');
        console.error('[runSeed]: 1. Check your DATABASE_URL in .env file');
        console.error(
          '[runSeed]:    Format: postgresql://username:password@host:port/database'
        );
        console.error(
          '[runSeed]:    Example: postgresql://postgres:postgres@localhost:5432/myoro_arbihawk\n'
        );
        console.error('[runSeed]: 2. If using Docker Compose, default is:');
        console.error(
          '[runSeed]:    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/myoro_arbihawk\n'
        );
      } else if (
        errorCode === '3D000' ||
        errorMessage.includes('does not exist')
      ) {
        console.error('[runSeed]: \n❌ Database does not exist!');
        console.error('[runSeed]: The database needs to be created.\n');
        console.error('[runSeed]: To fix:');
        console.error('[runSeed]: 1. Run: bun run db:setup');
        console.error(
          '[runSeed]: 2. Or manually: createdb -U postgres myoro_arbihawk\n'
        );
      } else if (
        errorMessage.includes('relation') &&
        errorMessage.includes('does not exist')
      ) {
        console.error('[runSeed]: \n❌ Database tables do not exist!');
        console.error('[runSeed]: Migrations need to be run.\n');
        console.error('[runSeed]: To fix:');
        console.error('[runSeed]: 1. Run: bun run db:migrate');
        console.error('[runSeed]: 2. Or run full setup: bun run setup\n');
      } else {
        console.error('[runSeed]: \n❌ Database error:', errorCode);
        console.error(
          '[runSeed]: Check your DATABASE_URL and PostgreSQL connection.\n'
        );
      }
    } else {
      console.error('[runSeed]: \n❌ Unknown error occurred');
      console.error(
        '[runSeed]: Check your DATABASE_URL and PostgreSQL connection.\n'
      );
    }

    process.exit(1);
  }
}

// Run seed if this file is executed directly
// This check works when running with: bun run src/db/seed.ts
if (process.argv[1]?.endsWith('seed.ts')) {
  runSeed();
}
