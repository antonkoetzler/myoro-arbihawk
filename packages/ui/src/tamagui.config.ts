import { createTamagui, createTokens } from '@tamagui/core';
import { shorthands } from '@tamagui/shorthands';
import { themes, tokens as defaultTokens } from '@tamagui/config/v3';

const tokens = createTokens({
  ...defaultTokens,
  color: {
    ...defaultTokens.color,
    primary: '#6366f1',
    primaryHover: '#4f46e5',
    primaryActive: '#4338ca',
    secondary: '#64748b',
    success: '#22c55e',
    warning: '#f59e0b',
    error: '#ef4444',
    background: '#ffffff',
    backgroundDark: '#0f172a',
    surface: '#f8fafc',
    surfaceDark: '#1e293b',
    text: '#0f172a',
    textDark: '#f8fafc',
    textMuted: '#64748b',
  },
});

export const config = createTamagui({
  tokens,
  themes,
  shorthands,
  fonts: {
    heading: {
      family: 'System',
      weight: {
        1: '400',
        2: '500',
        3: '600',
        4: '700',
      },
      size: {
        1: 12,
        2: 14,
        3: 16,
        4: 18,
        5: 20,
        6: 24,
        7: 28,
        8: 32,
        9: 40,
        10: 48,
      },
    },
    body: {
      family: 'System',
      weight: {
        1: '400',
        2: '500',
      },
      size: {
        1: 12,
        2: 14,
        3: 16,
        4: 18,
      },
    },
  },
});

export type AppConfig = typeof config;

declare module 'tamagui' {
  interface TamaguiCustomConfig extends AppConfig {}
}

