'use client';

import { useMemo } from 'react';
import { useLanguageStore } from '@/stores/language-store';
import { getTranslations, type TranslationPath, t as getT } from '@/lib/i18n';

/**
 * Hook to access translations in React components.
 *
 * Automatically uses the current language from the language store.
 *
 * @returns Translation function and full translations object
 *
 * @example
 * ```typescript
 * const { t, translations } = useTranslations();
 *
 * // Using the t function
 * <button>{t('auth.login')}</button>
 *
 * // Or direct access
 * <button>{translations.auth.login}</button>
 * ```
 */
export function useTranslations() {
  const language = useLanguageStore((state) => state.language);
  const translations = useMemo(() => getTranslations(language), [language]);

  const translationFn = useMemo(
    () => (path: TranslationPath) => getT(translations, path),
    [translations]
  );

  return {
    /** Type-safe translation function */
    t: translationFn,
    /** Full translations object for direct access */
    translations,
  };
}
