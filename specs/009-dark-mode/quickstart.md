# Quickstart: Dark Mode & Theming Testing Guide

## Prerequisites

- Frontend running (`npm run dev` in `frontend/`)
- Browser with OS dark mode toggle accessible (Windows: Settings > Personalization > Colors)

## Scenario 1: System Theme Detection

1. Set OS to **dark mode**
2. Open http://localhost:3000 in a fresh browser (clear localStorage first)
3. **Expected**: App loads with dark palette — dark backgrounds, light text
4. Set OS to **light mode**
5. **Expected**: App immediately switches to light palette without page reload

## Scenario 2: Manual Theme Toggle

1. Open the app in any theme
2. Find the theme toggle button in the **header** (sun/moon/monitor icon)
3. Click to cycle: Light → Dark → System
4. **Expected**: Each click immediately changes the palette
5. When set to "System", change OS preference — app should follow

## Scenario 3: Persistence

1. Set theme to **Dark** via the toggle
2. Close the browser tab entirely
3. Reopen http://localhost:3000
4. **Expected**: App loads in dark mode with **no flash** of light mode

## Scenario 4: All Pages Dark Mode Audit

Navigate to each page in dark mode and verify readability:

| Page | Key Elements to Check |
|------|----------------------|
| `/login` | Form fields, labels, button, error message |
| `/setup` | Form fields, labels, button, loading state |
| `/chat` | Message bubbles (user + assistant), input, streaming dots, error banner |
| `/chat` (sidebar) | Conversation list, active item highlight, new button, timestamps |
| `/memory` | Memory cards, type badges, search input, filter buttons, delete dialog |
| `/knowledge` | Entity cards, type badges, search, expand/collapse, relationships list |
| `/admin` | User table, create form, action buttons, status badges |

## Scenario 5: Code Block Theming

1. In dark mode, send a message asking for code (e.g., "show me a Python function")
2. **Expected**: Code block uses dark syntax highlighting theme (dark background, colored syntax)
3. Switch to light mode
4. **Expected**: Code block switches to light syntax highlighting theme

## Scenario 6: FOUC Check

1. Set theme to **Dark**
2. Hard refresh the page (Ctrl+Shift+R)
3. **Expected**: Page loads dark immediately — no flash of white/light theme
4. Repeat with **Light** theme selected and dark OS preference
5. **Expected**: Page loads light immediately — no flash of dark theme

## Scenario 7: Edge Cases

1. Open DevTools → Application → Local Storage → delete the `theme` key
2. Refresh page
3. **Expected**: Falls back to system preference (no error, no broken UI)
4. Set localStorage `theme` to an invalid value (e.g., `"banana"`)
5. Refresh page
6. **Expected**: Falls back gracefully to system preference
