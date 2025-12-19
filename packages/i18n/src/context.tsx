import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import type { Translations, SupportedLocale } from './types';
import { SUPPORTED_LOCALES } from './types';

// Import all locales
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
import zhTW from './locales/zh-TW.json';

const locales: Record<SupportedLocale, Translations> = {
  en, ar, de, es, fr, hi, id, it, ja, ko, nl, pl, pt, ru, th, tr, vi, zh, 'zh-TW': zhTW,
};

// Validate at build time that all locales have the same structure
type ValidateLocale<T> = T extends Translations ? T : never;
const _validateLocales: Record<SupportedLocale, ValidateLocale<Translations>> = locales;

interface I18nContextValue {
  locale: SupportedLocale;
  setLocale: (locale: SupportedLocale) => void;
  t: Translations;
}

const I18nContext = createContext<I18nContextValue | null>(null);

interface I18nProviderProps {
  children: ReactNode;
  defaultLocale?: SupportedLocale;
}

export function I18nProvider({ children, defaultLocale = 'en' }: I18nProviderProps) {
  const [locale, setLocaleState] = useState<SupportedLocale>(defaultLocale);

  const setLocale = useCallback((newLocale: SupportedLocale) => {
    if (SUPPORTED_LOCALES.includes(newLocale)) {
      setLocaleState(newLocale);
    } else {
      console.warn(`Unsupported locale: ${newLocale}`);
    }
  }, []);

  const value: I18nContextValue = {
    locale,
    setLocale,
    t: locales[locale],
  };

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}

export function useTranslations(): Translations {
  return useI18n().t;
}

export function useLocale(): [SupportedLocale, (locale: SupportedLocale) => void] {
  const { locale, setLocale } = useI18n();
  return [locale, setLocale];
}

