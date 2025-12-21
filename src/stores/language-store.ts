'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { LanguageCode } from '@/lib/i18n/types';

interface LanguageState {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
}

/**
 * Zustand store for language preferences.
 *
 * Persists language selection to localStorage.
 */
export const useLanguageStore = create<LanguageState>()(
  persist(
    (set) => ({
      language: 'en',
      setLanguage: (lang) => set({ language: lang }),
    }),
    {
      name: 'language-storage',
    }
  )
);
