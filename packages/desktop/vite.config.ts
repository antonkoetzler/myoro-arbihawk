import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { tamaguiPlugin } from '@tamagui/vite-plugin';

export default defineConfig({
  plugins: [
    react(),
    tamaguiPlugin({
      config: './tamagui.config.ts',
      components: ['tamagui', '@repo/ui'],
    }),
  ],
  base: './',
  build: {
    outDir: 'dist',
  },
  server: {
    port: 5174,
  },
});

