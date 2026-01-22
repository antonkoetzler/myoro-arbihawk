// Messages that indicate a new task is starting (should clear logs)
export const TASK_START_PATTERNS: readonly string[] = [
  'Starting model training',
  'Starting data collection',
  'Starting full automation cycle',
  'Starting betting cycle',
] as const;

// Define which queries are needed for each tab
export const TAB_QUERIES: Record<string, readonly string[]> = {
  system: ['health', 'errors', 'dbStats', 'status'] as const,
  bets: ['bankroll', 'bets'] as const,
  betting: ['bets', 'bankroll'] as const,
  automation: ['status'] as const,
  models: ['models'] as const,
  logs: [] as const, // No polling needed - WebSocket handles it
} as const;

// Database stat tooltips
export const dbStatTooltips: Record<string, string> = {
  fixtures: 'Total number of match fixtures stored in the database',
  odds: 'Total betting odds records across all fixtures',
  bets: 'Total bets placed through the system',
  models: 'Number of trained model versions',
  scores: 'Match scores collected from external sources',
  ingestions: 'Number of data ingestion operations performed',
};

// Market descriptions for models
export const marketDescriptions: Record<string, string> = {
  '1x2':
    'Match Result: Predicts the match outcome - Home Win (1), Draw (X), or Away Win (2)',
  over_under:
    'Total Goals: Predicts if the total number of goals scored by both teams will be Over 2.5 or Under 2.5',
  btts: 'Both Teams To Score (BTTS): Predicts whether both teams will score at least one goal each (Yes) or if at least one team fails to score (No)',
};
