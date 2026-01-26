/**
 * Search utilities for normalizing and sanitizing search queries
 */

/**
 * Normalize text by removing accents and converting to lowercase
 * Handles international characters like ç, é, á, ú, etc.
 */
export function normalizeSearchText(text: string): string {
  if (!text) return '';
  
  return text
    .toLowerCase()
    .normalize('NFD') // Decompose characters (é -> e + ´)
    .replace(/[\u0300-\u036f]/g, '') // Remove diacritics
    .trim();
}

/**
 * Check if search query matches text (case-insensitive, accent-insensitive)
 */
export function matchesSearch(query: string, text: string | null | undefined): boolean {
  if (!text) return false;
  if (!query) return true;
  
  const normalizedQuery = normalizeSearchText(query);
  const normalizedText = normalizeSearchText(text);
  
  return normalizedText.includes(normalizedQuery);
}

/**
 * Search across multiple fields in a bet object
 */
export function searchBet(bet: any, query: string): boolean {
  if (!query) return true;
  
  const normalizedQuery = normalizeSearchText(query);
  
  // Search across all relevant fields
  const fieldsToSearch = [
    bet.tournament_name,
    bet.market_name,
    bet.outcome_name,
    bet.result,
    bet.model_market,
    bet.odds?.toString(),
    bet.stake?.toString(),
    bet.payout?.toString(),
  ].filter(Boolean);
  
  return fieldsToSearch.some(field => 
    normalizeSearchText(String(field)).includes(normalizedQuery)
  );
}
