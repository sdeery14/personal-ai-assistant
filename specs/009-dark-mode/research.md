# Research: Dark Mode & Theming

## Decision 1: Theme Management Library

**Decision**: Use `next-themes` (npm package)

**Rationale**: Industry-standard library for Next.js dark mode (6.5k+ GitHub stars). Handles FOUC prevention, localStorage persistence, system preference detection, and cross-tab sync out of the box. Compatible with App Router and server components.

**Alternatives considered**:
- Manual implementation with localStorage + useEffect: More control but requires custom FOUC prevention script and significant boilerplate
- CSS-only with `prefers-color-scheme`: Cannot persist user preference or provide manual toggle
- `react-dark-mode` / `use-dark-mode`: Less popular, no App Router-specific optimizations

## Decision 2: Tailwind CSS v4 Dark Mode Strategy

**Decision**: Use `@custom-variant dark (&:where(.dark, .dark *));` in globals.css with class-based toggling

**Rationale**: Tailwind v4 moved configuration from `tailwind.config.js` to CSS directives. The `darkMode: 'class'` config option from v3 no longer exists. The `@custom-variant` directive enables `dark:` utility classes when a `.dark` class is present on an ancestor element (applied to `<html>` by next-themes).

**Alternatives considered**:
- Default `prefers-color-scheme` (no custom variant): Only follows OS preference, cannot support manual toggle or persistent preference
- Data attribute approach (`data-theme="dark"`): Works but class-based is more standard with Tailwind conventions
- Tailwind v3 config-based approach: Not compatible with v4 CSS-first architecture

## Decision 3: FOUC Prevention

**Decision**: Rely on next-themes built-in FOUC prevention (no manual script)

**Rationale**: next-themes automatically injects a blocking `<script>` in `<head>` that reads localStorage and applies the theme class before React hydration. This is battle-tested across thousands of Next.js apps. Requires only `suppressHydrationWarning` on `<html>`.

**Alternatives considered**:
- Manual inline script in layout: More control but requires maintenance and testing
- Server-side cookie-based detection: Adds HTTP overhead, doesn't work with static generation
- No prevention (accept FOUC): Poor user experience, violates spec requirement FR-006

## Decision 4: Syntax Highlighting Theme Pair

**Decision**: `oneLight` (light) / `vscDarkPlus` (dark) from react-syntax-highlighter Prism themes

**Rationale**: VS Code themes are the most widely recognized by developers. `vscDarkPlus` provides excellent contrast on dark backgrounds. `oneLight` is clean and readable on light backgrounds. Both are bundled with react-syntax-highlighter (already installed).

**Alternatives considered**:
- `materialLight` / `materialDark`: Good but less familiar to most developers
- `prism` / `oneDark`: Default Prism is less polished for light mode
- `ghcolors` / `nightOwl`: GitHub light + Night Owl dark is a good combo but inconsistent aesthetic
- `react-shiki`: Newer library with built-in light-dark CSS function, but less mature

## Decision 5: Theme Toggle UX Pattern

**Decision**: 3-way cycle button in the Header component showing current state icon

**Rationale**: A single button that cycles through Light → Dark → System is the most space-efficient approach for the header. Shows a sun icon (light), moon icon (dark), or monitor icon (system). This is the standard pattern used by Tailwind docs, Next.js docs, and most modern web apps.

**Alternatives considered**:
- Dropdown menu with 3 options: Uses more space, requires extra click to dismiss
- Segmented control / radio buttons: Takes too much horizontal space in header
- Icon-only toggle (light/dark, no system): Missing the "System" option required by spec
