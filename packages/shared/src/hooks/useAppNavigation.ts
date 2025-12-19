/**
 * Navigation abstraction interface
 * Platform-specific implementations wrap their respective navigation libraries
 */
export interface AppNavigation {
  navigate: (route: string, params?: Record<string, unknown>) => void;
  goBack: () => void;
  replace: (route: string, params?: Record<string, unknown>) => void;
}

// Navigation context is set up at the platform level
// Web: uses react-router-dom
// Mobile: uses expo-router / react-navigation

