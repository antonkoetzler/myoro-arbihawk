/**
 * Type definition for all translation keys.
 *
 * Add new keys here, then implement them in all language files.
 * TypeScript will error if any language is missing a key.
 */
export type TranslationKeys = {
  auth: {
    login: string;
    signup: string;
    email: string;
    password: string;
    submit: string;
    loading: string;
    logout: string;
    noAccount: string;
    hasAccount: string;
    userExists: string;
    invalidCredentials: string;
  };
  theme: {
    light: string;
    dark: string;
    system: string;
    title: string;
  };
  greeting: {
    hello: string;
  };
  errors: {
    generic: string;
  };
  leagues: {
    title: string;
    browse: string;
    subscribe: string;
    subscribed: string;
    active: string;
    inactive: string;
    country: string;
    noLeagues: string;
  };
  subscriptions: {
    title: string;
    mySubscriptions: string;
    active: string;
    canceled: string;
    cancel: string;
    cancelConfirm: string;
    noSubscriptions: string;
    renewsOn: string;
  };
  matches: {
    title: string;
    upcoming: string;
    live: string;
    finished: string;
    vs: string;
    date: string;
    time: string;
    score: string;
    all: string;
    noMatchesFound: string;
    tbd: string;
  };
  matchDetail: {
    statistics: string;
    possession: string;
    shots: string;
    shotsOnTarget: string;
    corners: string;
    bettingRecommendations: string;
    loadingRecommendations: string;
    noRecommendations: string;
    matchNotFound: string;
  };
  standings: {
    leagueTable: string;
    noData: string;
    position: string;
    team: string;
    played: string;
    wins: string;
    draws: string;
    losses: string;
    goalDifference: string;
    points: string;
  };
  common: {
    leagueNotFound: string;
    reloadPage: string;
    goHome: string;
    somethingWentWrong: string;
    unexpectedError: string;
  };
  stats: {
    title: string;
    noTeams: string;
    wins: string;
    draws: string;
    losses: string;
    totalGoals: string;
    totalShots: string;
    shotsOnTarget: string;
    goalsPerMatch: string;
  };
};

/**
 * Supported language codes.
 */
export type LanguageCode =
  | 'ar' // Arabic
  | 'de' // German
  | 'en' // English
  | 'es' // Spanish
  | 'fr' // French
  | 'hi' // Hindi
  | 'id' // Indonesian
  | 'it' // Italian
  | 'ja' // Japanese
  | 'ko' // Korean
  | 'nl' // Dutch
  | 'pl' // Polish
  | 'pt' // Portuguese
  | 'ru' // Russian
  | 'th' // Thai
  | 'tr' // Turkish
  | 'vi' // Vietnamese
  | 'zh' // Chinese (Simplified)
  | 'zh_TW'; // Chinese (Traditional)
