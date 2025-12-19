import en from './locales/en.json';

// Type definitions derived from the English locale (source of truth)
export type Translations = typeof en;
export type TranslationKey = keyof Translations;
export type CommonTranslations = Translations['common'];
export type CounterTranslations = Translations['counter'];
export type SettingsTranslations = Translations['settings'];

// Supported locales
export const SUPPORTED_LOCALES = [
  'en', 'ar', 'de', 'es', 'fr', 'hi', 'id', 'it', 'ja',
  'ko', 'nl', 'pl', 'pt', 'ru', 'th', 'tr', 'vi', 'zh', 'zh-TW'
] as const;

export type SupportedLocale = typeof SUPPORTED_LOCALES[number];

// Locale metadata for display
export const LOCALE_NAMES: Record<SupportedLocale, string> = {
  en: 'English',
  ar: 'العربية',
  de: 'Deutsch',
  es: 'Español',
  fr: 'Français',
  hi: 'हिन्दी',
  id: 'Bahasa Indonesia',
  it: 'Italiano',
  ja: '日本語',
  ko: '한국어',
  nl: 'Nederlands',
  pl: 'Polski',
  pt: 'Português',
  ru: 'Русский',
  th: 'ไทย',
  tr: 'Türkçe',
  vi: 'Tiếng Việt',
  zh: '简体中文',
  'zh-TW': '繁體中文',
};

