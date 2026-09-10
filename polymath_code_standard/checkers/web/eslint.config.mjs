// SPDX-FileCopyrightText: 2026 Polymath Robotics, Inc.
// SPDX-License-Identifier: Apache-2.0
//
// Polymath baseline ESLint configuration.

import js from "@eslint/js";
import prettier from "eslint-config-prettier";
import a11y from "eslint-plugin-jsx-a11y";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

const REACT_FILES = ["**/*.jsx", "**/*.tsx"];

// Comma-separated list, set by the hook from its --framework arguments.
const frameworks = new Set(
  (process.env.POLYMATH_ESLINT_FRAMEWORKS ?? "")
    .split(",")
    .map((name) => name.trim())
    .filter(Boolean),
);

const frameworkConfigs = [];

if (frameworks.has("next")) {
  const next = (await import("@next/eslint-plugin-next")).default;
  frameworkConfigs.push(
    next.configs.recommended,
    next.configs["core-web-vitals"],
  );
}

if (frameworks.has("storybook")) {
  const storybook = (await import("eslint-plugin-storybook")).default;
  frameworkConfigs.push(...storybook.configs["flat/recommended"]);
}

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
  },
  // Allow require() in CommonJS files.
  {
    files: ["**/*.cjs"],
    rules: { "@typescript-eslint/no-require-imports": "off" },
  },
  {
    files: REACT_FILES,
    ...react.configs.flat.recommended,
    settings: { react: { version: "detect" } },
  },
  { files: REACT_FILES, ...react.configs.flat["jsx-runtime"] },
  { files: REACT_FILES, ...reactHooks.configs.flat.recommended },
  { files: REACT_FILES, ...a11y.flatConfigs.recommended },
  ...frameworkConfigs,
  // Last: turns off every formatting rule the blocks above enabled.
  prettier,
];
