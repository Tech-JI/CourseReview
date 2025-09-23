import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import prettierConfig from "eslint-config-prettier";
import globals from "globals";

export default [
  // Global ignores
  {
    ignores: ["dist", "node_modules"],
  },

  // Base configuration for all JavaScript/Vue files
  js.configs.recommended,
  ...pluginVue.configs["flat/recommended"],

  // Custom rules and settings
  {
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        ...globals.browser, // For browser environments like document, window
        process: "readonly", // To allow process.env.NODE_ENV
        "import.meta": "readonly", // Vite uses import.meta.env
      },
    },
    rules: {
      "no-console": process.env.NODE_ENV === "production" ? "warn" : "off",
      "no-debugger": process.env.NODE_ENV === "production" ? "warn" : "off",
      "vue/multi-word-component-names": "off",
    },
  },

  // Turns off any ESLint rules that would conflict with Prettier's formatting.
  prettierConfig,
];
