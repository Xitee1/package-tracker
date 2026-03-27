# Form Dirty Tracking Design

## Goal

Add dirty tracking to all settings/config forms so that:

1. Save buttons are disabled unless the form state differs from the last saved state
2. Reverting changes back to original state disables the button again
3. Navigating away from a dirty form triggers a confirmation dialog

## Approach

Use VueUse's `useRefHistory` wrapped in a project-specific `useDirtyTracking` composable. VueUse is tree-shakeable (~1.2 KB for `useRefHistory`) and a well-maintained standard utility library for Vue 3.

## Composable: `useDirtyTracking`

**File:** `frontend/src/composables/useDirtyTracking.ts`

### API

```typescript
const { isDirty, reset } = useDirtyTracking(form, options?)
```

| Return | Type | Description |
|--------|------|-------------|
| `isDirty` | `ComputedRef<boolean>` | `true` when current form state differs from the clean baseline |
| `reset` | `() => void` | Sets current state as the new clean baseline |

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `guard` | `boolean` | `true` | Register `onBeforeRouteLeave` and `beforeunload` guards |

### Internal mechanism

- Wraps `useRefHistory(form, { deep: true })` from `@vueuse/core`
- `isDirty` is derived from `history.length > 1` (more than the initial commit)
- `reset()` calls the history's `clear()` to set a new clean baseline
- Deep clone uses the default `JSON.parse(JSON.stringify())` which is sufficient for all form data in this project (strings, numbers, booleans, plain arrays/objects)

### Navigation guard

When `guard: true` (default):

- Registers `onBeforeRouteLeave` from `vue-router`: if `isDirty`, shows `window.confirm()` with localized message. Cancelling prevents navigation.
- Registers `beforeunload` event on `window`: if `isDirty`, triggers browser-native "unsaved changes" dialog on tab close/reload.
- Both listeners are cleaned up via `onUnmounted`.

### i18n

New key in both `en.json` and `de.json`:

- `common.unsavedChanges` — e.g. "You have unsaved changes. Are you sure you want to leave?"

## Save button integration

Each form's save button changes from:

```html
<button :disabled="saving">
```

to:

```html
<button :disabled="saving || !isDirty">
```

Existing Tailwind classes (`disabled:opacity-50 disabled:cursor-not-allowed`) handle the visual styling automatically.

## Reset points

- **After successful save:** Call `reset()` after the API call succeeds, so the button disables again.
- **After async data load:** Call `reset()` after populating the form ref from the server response in `onMounted`, so the server state (not the empty default) is the clean baseline.

## Forms to update

| Form | File | Dirty tracking | Navigation guard |
|------|------|---------------|-----------------|
| Queue Settings | `views/admin/QueueSettingsView.vue` | Yes | Yes |
| SMTP Config | `views/admin/AdminSmtpSettingsView.vue` | Yes | Yes |
| IMAP Settings | `modules/providers/email-user/AdminImapSettingsView.vue` | Yes | Yes |
| LLM Config | `modules/analysers/llm/AdminLLMConfigView.vue` | Yes | Yes |
| Global Mail (Connection + Mapping) | `modules/providers/email-global/AdminGlobalMailView.vue` | Yes | Yes |
| User IMAP Accounts | `modules/providers/email-user/UserImapAccountsView.vue` | Yes | Yes |
| Email Notifications (Events) | `modules/notifiers/notify-email/UserNotifyEmailView.vue` | Yes | Yes |
| Webhook Config + Events | `modules/notifiers/notify-webhook/UserNotifyWebhookView.vue` | Yes | Yes |
| Profile (Password) | `views/ProfileView.vue` | Yes | Yes |
| Order Form Modal | `components/OrderFormModal.vue` | Yes | No (modal) |
| Add User | `views/admin/UsersView.vue` | Yes | No (collapsible) |

### Excluded forms

| Form | Reason |
|------|--------|
| LoginView | Auth form, no meaningful "unsaved state" |
| UserForwardingView | Single-input inline form, not a settings page |
| AdminNotifyEmailView | Module toggle only, no form |
| AdminNotifyWebhookView | Module toggle only, no form |

## Dependencies

- **New:** `@vueuse/core` (tree-shakeable, only `useRefHistory` imported)
- **Existing:** `vue-router` (for `onBeforeRouteLeave`), `vue-i18n` (for confirm text)
