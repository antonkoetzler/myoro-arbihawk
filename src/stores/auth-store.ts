'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  token: string | null;
  setToken: (token: string | null) => void;
  clearAuth: () => void;
}

/**
 * Zustand store for authentication state.
 *
 * Manages JWT token and persists it to localStorage.
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token:
        typeof window !== 'undefined' ? localStorage.getItem('token') : null,
      setToken: (token) => {
        set({ token });
        if (token) {
          localStorage.setItem('token', token);
        } else {
          localStorage.removeItem('token');
        }
      },
      clearAuth: () => {
        set({ token: null });
        localStorage.removeItem('token');
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);
