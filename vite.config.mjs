import { defineConfig } from 'vite';

export default defineConfig({
  base: process.env.GITHUB_ACTIONS ? '/Vessel/' : (process.env.ELECTRON_BUILD ? './' : '/'),
});
