import type { LanguageCode, TranslationKeys } from './types';

export type { TranslationKeys, LanguageCode };
import en from './locales/en.json';
import ar from './locales/ar.json';
import de from './locales/de.json';
import es from './locales/es.json';
import fr from './locales/fr.json';
import hi from './locales/hi.json';
import id from './locales/id.json';
import it from './locales/it.json';
import ja from './locales/ja.json';
import ko from './locales/ko.json';
import nl from './locales/nl.json';
import pl from './locales/pl.json';
import pt from './locales/pt.json';
import ru from './locales/ru.json';
import th from './locales/th.json';
import tr from './locales/tr.json';
import vi from './locales/vi.json';
import zh from './locales/zh.json';
import zh_TW from './locales/zh_TW.json';

/**
 * All translations mapped by language code.
 *
 * TypeScript ensures all languages implement TranslationKeys.
 */
const translations: Record<LanguageCode, TranslationKeys> = {
  en,
  ar,
  de,
  es,
  fr,
  hi,
  id,
  it,
  ja,
  ko,
  nl,
  pl,
  pt,
  ru,
  th,
  tr,
  vi,
  zh,
  zh_TW,
};

/**
 * Default language code.
 */
export const DEFAULT_LANGUAGE: LanguageCode = 'en';

/**
 * Gets translations for a specific language.
 *
 * @param lang - Language code
 * @returns Translation object for the language
 */
export function getTranslations(
  lang: LanguageCode = DEFAULT_LANGUAGE
): TranslationKeys {
  return translations[lang] || translations[DEFAULT_LANGUAGE];
}

/**
 * Type-safe helper to get nested translation values.
 *
 * @example
 * ```typescript
 * const t = useTranslations();
 * const loginText = t('auth.login');
 * ```
 */
export type TranslationPath =
  | 'auth.login'
  | 'auth.signup'
  | 'auth.email'
  | 'auth.password'
  | 'auth.submit'
  | 'auth.loading'
  | 'auth.noAccount'
  | 'auth.hasAccount'
  | 'auth.userExists'
  | 'auth.invalidCredentials'
  | 'greeting.hello'
  | 'errors.generic'
  | 'leagues.title'
  | 'leagues.browse'
  | 'leagues.subscribe'
  | 'leagues.subscribed'
  | 'leagues.active'
  | 'leagues.inactive'
  | 'leagues.country'
  | 'leagues.noLeagues'
  | 'subscriptions.title'
  | 'subscriptions.mySubscriptions'
  | 'subscriptions.active'
  | 'subscriptions.canceled'
  | 'subscriptions.cancel'
  | 'subscriptions.cancelConfirm'
  | 'subscriptions.noSubscriptions'
  | 'subscriptions.renewsOn'
  | 'matches.title'
  | 'matches.upcoming'
  | 'matches.live'
  | 'matches.finished'
  | 'matches.vs'
  | 'matches.date'
  | 'matches.time'
  | 'matches.score';

/**
 * Gets a translation value by path.
 *
 * @param translations - Translation object
 * @param path - Dot-separated path to translation key
 * @returns Translated string
 */
export function t(
  translations: TranslationKeys,
  path: TranslationPath
): string {
  const [section, key] = path.split('.') as [keyof TranslationKeys, string];
  const sectionObj = translations[section] as Record<string, string>;
  return sectionObj[key] || path;
}
