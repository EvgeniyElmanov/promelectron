import { defineConfig, globalIgnores } from 'eslint/config'
import globals from 'globals'
import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import pluginOxlint from 'eslint-plugin-oxlint'
import skipFormatting from 'eslint-config-prettier/flat'

export default defineConfig([
  {
    name: 'app/files-to-lint',
    files: ['**/*.{vue,js,mjs,jsx}'],
  },

  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**']),

  {
    name: 'app/browser-globals',
    files: ['src/**/*.{vue,js,mjs,jsx}'],
    languageOptions: {
      globals: {
        ...globals.browser,
      },
    },
  },

  {
    name: 'app/node-globals',
    files: ['*.config.js', 'e2e/**/*.js', 'tests/**/*.js'],
    languageOptions: {
      globals: {
        ...globals.node,
        ...globals.browser,
      },
    },
  },

  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],

  {
    name: 'app/legacy-single-word-components',
    files: [
      'src/components/Header.vue',
      'src/components/Skeleton.vue',
      'src/views/Admin.vue',
      'src/views/Cart.vue',
      'src/views/Checkout.vue',
      'src/views/Favorites.vue',
      'src/views/Login.vue',
      'src/views/Notifications.vue',
      'src/views/Orders.vue',
      'src/views/Products.vue',
      'src/views/Profile.vue',
      'src/views/Register.vue',
    ],
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },

  ...pluginOxlint.buildFromOxlintConfigFile('.oxlintrc.json'),

  skipFormatting,
])
