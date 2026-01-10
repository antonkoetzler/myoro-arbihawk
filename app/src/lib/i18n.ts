// Localization file.

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import enTranslations from './i18n/locales/en.json';
import arTranslations from './i18n/locales/ar.json';
import deTranslations from './i18n/locales/de.json';
import esTranslations from './i18n/locales/es.json';
import frTranslations from './i18n/locales/fr.json';
import hiTranslations from './i18n/locales/hi.json';
import idTranslations from './i18n/locales/id.json';
import itTranslations from './i18n/locales/it.json';
import jaTranslations from './i18n/locales/ja.json';
import koTranslations from './i18n/locales/ko.json';
import nlTranslations from './i18n/locales/nl.json';
import plTranslations from './i18n/locales/pl.json';
import ptTranslations from './i18n/locales/pt.json';
import ruTranslations from './i18n/locales/ru.json';
import thTranslations from './i18n/locales/th.json';
import trTranslations from './i18n/locales/tr.json';
import viTranslations from './i18n/locales/vi.json';
import zhTranslations from './i18n/locales/zh.json';
import zhTWTranslations from './i18n/locales/zh_TW.json';

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: enTranslations,
      },
      ar: {
        translation: arTranslations,
      },
      de: {
        translation: deTranslations,
      },
      es: {
        translation: esTranslations,
      },
      fr: {
        translation: frTranslations,
      },
      hi: {
        translation: hiTranslations,
      },
      id: {
        translation: idTranslations,
      },
      it: {
        translation: itTranslations,
      },
      ja: {
        translation: jaTranslations,
      },
      ko: {
        translation: koTranslations,
      },
      nl: {
        translation: nlTranslations,
      },
      pl: {
        translation: plTranslations,
      },
      pt: {
        translation: ptTranslations,
      },
      ru: {
        translation: ruTranslations,
      },
      th: {
        translation: thTranslations,
      },
      tr: {
        translation: trTranslations,
      },
      vi: {
        translation: viTranslations,
      },
      zh: {
        translation: zhTranslations,
      },
      'zh-TW': {
        translation: zhTWTranslations,
      },
    },
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
