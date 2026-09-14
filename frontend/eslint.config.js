// @ts-check
import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "node_modules"] },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      // next/core-web-vitals 가 켜 두던 것과 동일한 hooks 룰 2개만 켠다.
      // eslint-plugin-react-hooks v7 의 configs.recommended 는 React Compiler
      // 룰(purity 등)까지 포함해서, module-scope idCounter 변형(chat-window.tsx)
      // 처럼 이관과 무관한 기존 코드에서 새 위반이 나온다 — 범위를 최소로 둔다.
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
    },
  },
  {
    files: ["vite.config.ts", "tailwind.config.ts"],
    languageOptions: { globals: globals.node },
  },
);
