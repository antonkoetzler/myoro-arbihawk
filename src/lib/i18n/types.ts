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
    noAccount: string;
    hasAccount: string;
    userExists: string;
    invalidCredentials: string;
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
