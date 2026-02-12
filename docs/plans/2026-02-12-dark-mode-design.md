# Dark Mode Design

## Overview

Add dark mode to the Package Tracker frontend with system preference detection and a manual override toggle. No backend changes required.

## Approach

- Tailwind CSS 4 `dark:` variants on all components (idiomatic Tailwind pattern)
- Theme preference stored in localStorage (light / dark / system)
- Defaults to system preference, user can override via toggle
- Inline script in `index.html` prevents flash of wrong theme

## Infrastructure

### CSS (`main.css`)

Add one line to enable class-based dark mode alongside `prefers-color-scheme`:

```css
@import "tailwindcss";
@custom-variant dark (&:where(.dark, .dark *));
```

### Theme Init Script (`index.html`)

Inline `<script>` before the app mounts:

1. Read `localStorage.getItem('theme')` — `'light'`, `'dark'`, or `'system'` (default)
2. If `'system'` or absent, check `window.matchMedia('(prefers-color-scheme: dark)').matches`
3. Add/remove `.dark` class on `<html>`

Runs before first paint to prevent theme flash.

### Theme Store (`stores/theme.ts`)

New Pinia store:

- `preference` state: `'light' | 'dark' | 'system'`
- `setTheme(preference)` action: updates localStorage, toggles `.dark` on `<html>`, listens for `matchMedia` changes when `'system'`
- Initializes from localStorage on creation

### ThemeToggle Component (`components/ThemeToggle.vue`)

Three-segment icon control: Sun (light) | Monitor (system) | Moon (dark)

- Active segment highlighted with `bg-gray-200 dark:bg-gray-700`
- Inline SVG icons (Heroicons-style), no new dependencies
- Calls `themeStore.setTheme()` on click

## Sidebar Placement

Toggle lives at the bottom of the sidebar in `AppLayout.vue`, between nav links and user/logout:

```
┌─────────────┐
│  Logo       │
│─────────────│
│  Dashboard  │
│  Orders     │
│  Accounts   │
│  Settings   │
│─────────────│
│ ☀  🖥  🌙   │  ← ThemeToggle
│─────────────│
│  User/Logout│
└─────────────┘
```

Appears in mobile slide-out menu in the same position. Not shown on login/setup pages (system preference or last saved preference applies there).

## Color Mapping

### Base Elements

| Element            | Light                      | Dark                                  |
| ------------------ | -------------------------- | ------------------------------------- |
| Page background    | `bg-gray-50`               | `dark:bg-gray-950`                    |
| Card/sidebar bg    | `bg-white`                 | `dark:bg-gray-900`                    |
| Primary text       | `text-gray-900`            | `dark:text-white`                     |
| Secondary text     | `text-gray-500`            | `dark:text-gray-400`                  |
| Borders            | `border-gray-200`          | `dark:border-gray-700`                |
| Inputs             | `bg-white border-gray-300` | `dark:bg-gray-800 dark:border-gray-600` |
| Hover backgrounds  | `hover:bg-gray-100`        | `dark:hover:bg-gray-800`              |
| Active nav         | `bg-blue-50 text-blue-700` | `dark:bg-blue-900/30 dark:text-blue-400` |

### Status Badges

| Status           | Light                           | Dark                                          |
| ---------------- | ------------------------------- | --------------------------------------------- |
| Ordered          | `bg-blue-100 text-blue-800`     | `dark:bg-blue-900/40 dark:text-blue-300`      |
| Preparing        | `bg-yellow-100 text-yellow-800` | `dark:bg-yellow-900/40 dark:text-yellow-300`  |
| Shipped          | `bg-indigo-100 text-indigo-800` | `dark:bg-indigo-900/40 dark:text-indigo-300`  |
| In Transit       | `bg-orange-100 text-orange-800` | `dark:bg-orange-900/40 dark:text-orange-300`  |
| Out for Delivery | `bg-purple-100 text-purple-800` | `dark:bg-purple-900/40 dark:text-purple-300`  |
| Delivered        | `bg-green-100 text-green-800`   | `dark:bg-green-900/40 dark:text-green-300`    |

### Buttons

- Primary (`bg-blue-600`): works as-is in both themes
- Secondary/outline: add `dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800`
- Destructive: add corresponding `dark:` red variants

## Files to Change

### New files (2)
- `frontend/src/stores/theme.ts`
- `frontend/src/components/ThemeToggle.vue`

### Modified files (13)
- `frontend/src/assets/main.css` — `@custom-variant` line
- `frontend/index.html` — inline theme init script
- `frontend/src/components/AppLayout.vue` — dark variants + mount ThemeToggle
- `frontend/src/components/StatusBadge.vue` — dark status colors
- `frontend/src/views/LoginView.vue`
- `frontend/src/views/SetupView.vue`
- `frontend/src/views/DashboardView.vue`
- `frontend/src/views/OrdersView.vue`
- `frontend/src/views/OrderDetailView.vue`
- `frontend/src/views/AccountsView.vue`
- `frontend/src/views/SettingsView.vue`
- `frontend/src/views/AdminUsersView.vue`
- `frontend/src/views/AdminLLMConfigView.vue`

### Not changed
- Backend (no changes needed)
- `vite.config.ts`, router, API client, other stores
- No new dependencies
