import {
  boolean,
  integer,
  jsonb,
  pgEnum,
  pgTable,
  text,
  timestamp,
  uuid,
} from 'drizzle-orm/pg-core';

/**
 * Users table definition.
 *
 * Stores user account information including email and hashed passwords.
 * All timestamps are automatically set by the database.
 */
export const users = pgTable('users', {
  /** Unique user identifier (UUID v4) */
  id: uuid('id').defaultRandom().primaryKey(),
  /** User's email address (must be unique) */
  email: text('email').notNull().unique(),
  /** Bcrypt-hashed password (never store plain passwords) */
  passwordHash: text('password_hash').notNull(),
  /** Timestamp when user account was created */
  createdAt: timestamp('created_at').defaultNow().notNull(),
  /** Timestamp when user account was last updated */
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

/**
 * TypeScript type for a user row from the database.
 *
 * Use this when you need the type of a user object returned from queries.
 *
 * @example
 * ```typescript
 * const user: User = await findUserByEmail('user@example.com');
 * ```
 */
export type User = typeof users.$inferSelect;

/**
 * TypeScript type for creating a new user.
 *
 * Use this when inserting new users (id, createdAt, updatedAt are optional).
 *
 * @example
 * ```typescript
 * const newUser: NewUser = {
 *   email: 'user@example.com',
 *   passwordHash: await hashPassword('password123')
 * };
 * ```
 */
export type NewUser = typeof users.$inferInsert;

/**
 * Subscription status enum.
 */
export const subscriptionStatusEnum = pgEnum('subscription_status', [
  'active',
  'canceled',
  'past_due',
  'incomplete',
  'trialing',
]);

/**
 * Leagues table definition.
 *
 * Stores soccer league information from API-Football.
 */
export const leagues = pgTable('leagues', {
  /** Unique league identifier (UUID v4) */
  id: uuid('id').defaultRandom().primaryKey(),
  /** League name (e.g., "Premier League") */
  name: text('name').notNull(),
  /** Country name */
  country: text('country').notNull(),
  /** API-Football league ID */
  apiLeagueId: integer('api_league_id').notNull().unique(),
  /** League logo URL */
  logoUrl: text('logo_url'),
  /** Whether league is active and available for subscription */
  isActive: boolean('is_active').default(true).notNull(),
  /** Timestamp when league was created */
  createdAt: timestamp('created_at').defaultNow().notNull(),
  /** Timestamp when league was last updated */
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export type League = typeof leagues.$inferSelect;
export type NewLeague = typeof leagues.$inferInsert;

/**
 * Subscriptions table definition.
 *
 * Stores user subscriptions to leagues via Stripe.
 */
export const subscriptions = pgTable('subscriptions', {
  /** Unique subscription identifier (UUID v4) */
  id: uuid('id').defaultRandom().primaryKey(),
  /** User ID (foreign key to users) */
  userId: uuid('user_id')
    .notNull()
    .references(() => users.id, { onDelete: 'cascade' }),
  /** League ID (foreign key to leagues) */
  leagueId: uuid('league_id')
    .notNull()
    .references(() => leagues.id, { onDelete: 'cascade' }),
  /** Stripe subscription ID */
  stripeSubscriptionId: text('stripe_subscription_id').notNull().unique(),
  /** Stripe customer ID */
  stripeCustomerId: text('stripe_customer_id').notNull(),
  /** Subscription status */
  status: subscriptionStatusEnum('status').notNull(),
  /** End of current billing period */
  currentPeriodEnd: timestamp('current_period_end').notNull(),
  /** Timestamp when subscription was created */
  createdAt: timestamp('created_at').defaultNow().notNull(),
  /** Timestamp when subscription was last updated */
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export type Subscription = typeof subscriptions.$inferSelect;
export type NewSubscription = typeof subscriptions.$inferInsert;

/**
 * Teams table definition.
 *
 * Stores team information from API-Football.
 */
export const teams = pgTable('teams', {
  /** Unique team identifier (UUID v4) */
  id: uuid('id').defaultRandom().primaryKey(),
  /** League ID (foreign key to leagues) */
  leagueId: uuid('league_id')
    .notNull()
    .references(() => leagues.id, { onDelete: 'cascade' }),
  /** Team name */
  name: text('name').notNull(),
  /** Team logo URL */
  logoUrl: text('logo_url'),
  /** API-Football team ID */
  apiTeamId: integer('api_team_id').notNull(),
  /** Raw JSON data from API */
  rawData: jsonb('raw_data'),
  /** Timestamp when team was created */
  createdAt: timestamp('created_at').defaultNow().notNull(),
  /** Timestamp when team was last updated */
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export type Team = typeof teams.$inferSelect;
export type NewTeam = typeof teams.$inferInsert;

/**
 * Match status enum.
 */
export const matchStatusEnum = pgEnum('match_status', [
  'scheduled',
  'live',
  'finished',
  'postponed',
  'canceled',
]);

/**
 * Matches table definition.
 *
 * Stores match/fixture information from API-Football.
 */
export const matches = pgTable('matches', {
  /** Unique match identifier (UUID v4) */
  id: uuid('id').defaultRandom().primaryKey(),
  /** League ID (foreign key to leagues) */
  leagueId: uuid('league_id')
    .notNull()
    .references(() => leagues.id, { onDelete: 'cascade' }),
  /** Home team ID (foreign key to teams) */
  homeTeamId: uuid('home_team_id')
    .notNull()
    .references(() => teams.id, { onDelete: 'cascade' }),
  /** Away team ID (foreign key to teams) */
  awayTeamId: uuid('away_team_id')
    .notNull()
    .references(() => teams.id, { onDelete: 'cascade' }),
  /** Match date and time */
  date: timestamp('date').notNull(),
  /** Match status */
  status: matchStatusEnum('status').notNull().default('scheduled'),
  /** Home team score */
  homeScore: integer('home_score'),
  /** Away team score */
  awayScore: integer('away_score'),
  /** API-Football match ID */
  apiMatchId: integer('api_match_id').notNull().unique(),
  /** Raw JSON data from API */
  rawData: jsonb('raw_data'),
  /** Timestamp when match was created */
  createdAt: timestamp('created_at').defaultNow().notNull(),
  /** Timestamp when match was last updated */
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export type Match = typeof matches.$inferSelect;
export type NewMatch = typeof matches.$inferInsert;

/**
 * Players table definition.
 *
 * Stores player information from API-Football.
 */
export const players = pgTable('players', {
  /** Unique player identifier (UUID v4) */
  id: uuid('id').defaultRandom().primaryKey(),
  /** Team ID (foreign key to teams) */
  teamId: uuid('team_id')
    .notNull()
    .references(() => teams.id, { onDelete: 'cascade' }),
  /** Player name */
  name: text('name').notNull(),
  /** Player position */
  position: text('position'),
  /** API-Football player ID */
  apiPlayerId: integer('api_player_id').notNull(),
  /** Raw JSON data from API */
  rawData: jsonb('raw_data'),
  /** Timestamp when player was created */
  createdAt: timestamp('created_at').defaultNow().notNull(),
  /** Timestamp when player was last updated */
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export type Player = typeof players.$inferSelect;
export type NewPlayer = typeof players.$inferInsert;

/**
 * Match statistics table definition.
 *
 * Stores detailed match statistics.
 */
export const matchStats = pgTable('match_stats', {
  /** Unique stat identifier (UUID v4) */
  id: uuid('id').defaultRandom().primaryKey(),
  /** Match ID (foreign key to matches) */
  matchId: uuid('match_id')
    .notNull()
    .references(() => matches.id, { onDelete: 'cascade' }),
  /** Home team possession percentage */
  homePossession: integer('home_possession'),
  /** Away team possession percentage */
  awayPossession: integer('away_possession'),
  /** Home team shots */
  homeShots: integer('home_shots'),
  /** Away team shots */
  awayShots: integer('away_shots'),
  /** Home team shots on target */
  homeShotsOnTarget: integer('home_shots_on_target'),
  /** Away team shots on target */
  awayShotsOnTarget: integer('away_shots_on_target'),
  /** Home team corners */
  homeCorners: integer('home_corners'),
  /** Away team corners */
  awayCorners: integer('away_corners'),
  /** Home team fouls */
  homeFouls: integer('home_fouls'),
  /** Away team fouls */
  awayFouls: integer('away_fouls'),
  /** Home team yellow cards */
  homeYellowCards: integer('home_yellow_cards'),
  /** Away team yellow cards */
  awayYellowCards: integer('away_yellow_cards'),
  /** Home team red cards */
  homeRedCards: integer('home_red_cards'),
  /** Away team red cards */
  awayRedCards: integer('away_red_cards'),
  /** Timestamp when stats were created */
  createdAt: timestamp('created_at').defaultNow().notNull(),
  /** Timestamp when stats were last updated */
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

export type MatchStat = typeof matchStats.$inferSelect;
export type NewMatchStat = typeof matchStats.$inferInsert;

/**
 * Bet type enum.
 */
export const betTypeEnum = pgEnum('bet_type', ['win', 'draw', 'over', 'under']);

/**
 * Betting recommendations table definition.
 *
 * Stores AI-generated betting recommendations with confidence scores.
 */
export const bettingRecommendations = pgTable('betting_recommendations', {
  /** Unique recommendation identifier (UUID v4) */
  id: uuid('id').defaultRandom().primaryKey(),
  /** Match ID (foreign key to matches) */
  matchId: uuid('match_id')
    .notNull()
    .references(() => matches.id, { onDelete: 'cascade' }),
  /** Type of bet recommendation */
  betType: betTypeEnum('bet_type').notNull(),
  /** Recommendation (e.g., "Home Win", "Over 2.5") */
  recommendation: text('recommendation').notNull(),
  /** Confidence percentage (0-100) */
  confidencePercentage: integer('confidence_percentage').notNull(),
  /** Timestamp when recommendation was calculated */
  calculatedAt: timestamp('calculated_at').defaultNow().notNull(),
  /** Timestamp when recommendation was created */
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

export type BettingRecommendation = typeof bettingRecommendations.$inferSelect;
export type NewBettingRecommendation =
  typeof bettingRecommendations.$inferInsert;
