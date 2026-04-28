import js from "@eslint/js";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import globals from "globals";

const tsRules = {
  ...tsPlugin.configs.recommended.rules,
  "@typescript-eslint/no-explicit-any": "warn",
  "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
  // TypeScript's compiler already catches undefined variables; no-undef produces
  // false positives for Node/browser globals in TS projects.
  "no-undef": "off",
  "no-console": "off",
};

export default [
  js.configs.recommended,

  // Electron main process — Node.js environment
  {
    files: ["electron/**/*.ts"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        project: "./tsconfig.json",
        tsconfigRootDir: import.meta.dirname,
      },
      globals: { ...globals.node },
    },
    plugins: { "@typescript-eslint": tsPlugin },
    rules: tsRules,
  },

  // React renderer — browser environment
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        project: "./tsconfig.json",
        tsconfigRootDir: import.meta.dirname,
        ecmaFeatures: { jsx: true },
      },
      globals: { ...globals.browser },
    },
    plugins: { "@typescript-eslint": tsPlugin },
    rules: tsRules,
  },

  { ignores: ["out/**", "dist/**", "node_modules/**"] },
];
