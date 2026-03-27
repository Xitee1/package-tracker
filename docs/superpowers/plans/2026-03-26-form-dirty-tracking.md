# Form Dirty Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dirty tracking to all settings forms so save buttons are disabled until the form differs from its last-saved state, and navigating away from dirty forms shows a confirmation dialog.

**Architecture:** A custom Vue 3 composable (`useDirtyTracking`) snapshots the form ref as JSON on initialization and after each save, then deep-watches for changes. A companion `useDirtyGuard` helper handles navigation guards for views with multiple independent forms. No external form library needed.

**Tech Stack:** Vue 3 Composition API, vue-router (`onBeforeRouteLeave`), vue-i18n, TypeScript

**Spec deviation:** The design spec mentioned wrapping VueUse's `useRefHistory`, but `useRefHistory` tracks undo history (not value equality). When a user reverts a field to its original value, `useRefHistory` still reports dirty because undo history exists. A JSON snapshot comparison correctly detects that the value matches the original. No VueUse dependency is added.

---

### Task 1: Create `useDirtyTracking` composable

**Files:**
- Create: `frontend/src/composables/useDirtyTracking.ts`

- [ ] **Step 1: Create the composable file**

```typescript
// frontend/src/composables/useDirtyTracking.ts
import { ref, computed, watch, onUnmounted, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useI18n } from 'vue-i18n'

interface DirtyTrackingOptions {
  guard?: boolean
}

export function useDirtyTracking<T>(source: Ref<T>, options: DirtyTrackingOptions = {}) {
  const { guard = true } = options

  const snapshot = ref(JSON.stringify(source.value))
  const dirty = ref(false)

  watch(
    source,
    (val) => {
      dirty.value = JSON.stringify(val) !== snapshot.value
    },
    { deep: true },
  )

  const isDirty = computed(() => dirty.value)

  function reset() {
    snapshot.value = JSON.stringify(source.value)
    dirty.value = false
  }

  if (guard) {
    const { t } = useI18n()

    onBeforeRouteLeave(() => {
      if (dirty.value && !window.confirm(t('common.unsavedChanges'))) {
        return false
      }
    })

    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (dirty.value) {
        e.preventDefault()
      }
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    onUnmounted(() => {
      window.removeEventListener('beforeunload', onBeforeUnload)
    })
  }

  return { isDirty, reset }
}

export function useDirtyGuard(...dirtyRefs: Ref<boolean>[]) {
  const { t } = useI18n()
  const isAnyDirty = computed(() => dirtyRefs.some((d) => d.value))

  onBeforeRouteLeave(() => {
    if (isAnyDirty.value && !window.confirm(t('common.unsavedChanges'))) {
      return false
    }
  })

  const onBeforeUnload = (e: BeforeUnloadEvent) => {
    if (isAnyDirty.value) {
      e.preventDefault()
    }
  }
  window.addEventListener('beforeunload', onBeforeUnload)
  onUnmounted(() => {
    window.removeEventListener('beforeunload', onBeforeUnload)
  })
}
```

- [ ] **Step 2: Verify types**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: No errors related to `useDirtyTracking.ts`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useDirtyTracking.ts
git commit -m "feat: add useDirtyTracking composable for form change detection"
```

---

### Task 2: Add i18n keys

**Files:**
- Modify: `frontend/src/i18n/locales/en.json`
- Modify: `frontend/src/i18n/locales/de.json`

- [ ] **Step 1: Add `unsavedChanges` key to en.json**

In the `"common"` section, after the `"themeDark"` entry, add:

```json
"unsavedChanges": "You have unsaved changes. Are you sure you want to leave?"
```

- [ ] **Step 2: Add `unsavedChanges` key to de.json**

In the `"common"` section, after the `"themeDark"` entry, add:

```json
"unsavedChanges": "Du hast ungespeicherte Änderungen. Möchtest du die Seite wirklich verlassen?"
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/i18n/locales/en.json frontend/src/i18n/locales/de.json
git commit -m "feat: add unsavedChanges i18n keys for dirty tracking"
```

---

### Task 3: Integrate into QueueSettingsView

**Files:**
- Modify: `frontend/src/views/admin/QueueSettingsView.vue`

This is the reference pattern for all single-form views. Three changes per file:
1. Import `useDirtyTracking` and call it after the form ref
2. Call `reset()` after data fetch and after successful save
3. Add `|| !isDirty` to the save button's `:disabled`

- [ ] **Step 1: Add import**

At line 80, change:
```typescript
import { ref, onMounted } from 'vue'
```
to:
```typescript
import { ref, onMounted } from 'vue'
import { useDirtyTracking } from '@/composables/useDirtyTracking'
```

- [ ] **Step 2: Initialize dirty tracking**

After the form ref (after line 96), add:
```typescript
const { isDirty, reset: resetDirty } = useDirtyTracking(form)
```

- [ ] **Step 3: Call resetDirty after fetch**

In `fetchSettings()`, inside the `try` block after populating form fields (after line 104), add:
```typescript
    resetDirty()
```

Note: Place it inside `try`, after `form.value.max_per_user = ...`, so the snapshot captures the server data, not the default values.

- [ ] **Step 4: Call resetDirty after save**

In `handleSave()`, inside the `try` block after `saveSuccess.value = true` (after line 118), add:
```typescript
    resetDirty()
```

- [ ] **Step 5: Update save button**

At line 69, change:
```html
          :disabled="saving"
```
to:
```html
          :disabled="saving || !isDirty"
```

- [ ] **Step 6: Verify types**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/admin/QueueSettingsView.vue
git commit -m "feat: add dirty tracking to QueueSettingsView"
```

---

### Task 4: Integrate into AdminSmtpSettingsView

**Files:**
- Modify: `frontend/src/views/admin/AdminSmtpSettingsView.vue`

- [ ] **Step 1: Add import**

At line 201, after `import { ref, onMounted } from 'vue'`, add:
```typescript
import { useDirtyTracking } from '@/composables/useDirtyTracking'
```

- [ ] **Step 2: Initialize dirty tracking**

After the form ref (after line 220), add:
```typescript
const { isDirty, reset: resetDirty } = useDirtyTracking(form)
```

- [ ] **Step 3: Call resetDirty after fetch**

In `fetchConfig()`, inside the `try` block, after `form.value.sender_name = res.data.sender_name || ''` (after line 243), add:
```typescript
    resetDirty()
```

- [ ] **Step 4: Call resetDirty after save**

In `handleSave()`, inside the `try` block, after `saveSuccess.value = true` (after line 261), add:
```typescript
    resetDirty()
```

- [ ] **Step 5: Update save button**

At line 142, change:
```html
              :disabled="saving"
```
to:
```html
              :disabled="saving || !isDirty"
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/admin/AdminSmtpSettingsView.vue
git commit -m "feat: add dirty tracking to AdminSmtpSettingsView"
```

---

### Task 5: Integrate into AdminImapSettingsView

**Files:**
- Modify: `frontend/src/modules/providers/email-user/AdminImapSettingsView.vue`

- [ ] **Step 1: Add import**

At line 94, after `import { ref, computed, onMounted } from 'vue'`, add:
```typescript
import { useDirtyTracking } from '@/composables/useDirtyTracking'
```

- [ ] **Step 2: Initialize dirty tracking**

After the form ref (after line 121), add:
```typescript
const { isDirty, reset: resetDirty } = useDirtyTracking(form)
```

- [ ] **Step 3: Call resetDirty after fetch**

In `fetchSettings()`, inside the `try` block, after `form.value.check_uidvalidity = res.data.check_uidvalidity` (after line 129), add:
```typescript
    resetDirty()
```

- [ ] **Step 4: Call resetDirty after save**

In `handleSave()`, inside the `try` block, after `saveSuccess.value = true` (after line 143), add:
```typescript
    resetDirty()
```

- [ ] **Step 5: Update save button**

At line 81, change:
```html
              :disabled="saving"
```
to:
```html
              :disabled="saving || !isDirty"
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/modules/providers/email-user/AdminImapSettingsView.vue
git commit -m "feat: add dirty tracking to AdminImapSettingsView"
```

---

### Task 6: Integrate into AdminLLMConfigView

**Files:**
- Modify: `frontend/src/modules/analysers/llm/AdminLLMConfigView.vue`

Special consideration: `handleSave()` clears `form.value.api_key` after save (line 325). The snapshot after `resetDirty()` must capture this cleared state. Also, `providerSelect` is a separate ref that affects the form but isn't part of the form ref itself — changes to `providerSelect` that trigger `handleProviderChange()` will modify `form.value`, which the deep watcher will detect.

- [ ] **Step 1: Add import**

At line 196, after `import { ref, computed, onMounted } from 'vue'`, add:
```typescript
import { useDirtyTracking } from '@/composables/useDirtyTracking'
```

- [ ] **Step 2: Initialize dirty tracking**

After the form ref (after line 227), add:
```typescript
const { isDirty, reset: resetDirty } = useDirtyTracking(form)
```

- [ ] **Step 3: Call resetDirty after fetch**

In `fetchConfig()`, inside the `try` block, after the closing `}` of `if (res.data)` (after line 298), add:
```typescript
    resetDirty()
```

Note: Place inside `try` but after the `if (res.data)` block so it captures whatever form state resulted.

- [ ] **Step 4: Call resetDirty after save**

In `handleSave()`, inside the `try` block, after `form.value.api_key = ''` (after line 325), add:
```typescript
    resetDirty()
```

This captures the post-save state where `api_key` is cleared.

- [ ] **Step 5: Update save button**

At line 155, change:
```html
              :disabled="saving"
```
to:
```html
              :disabled="saving || !isDirty"
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/modules/analysers/llm/AdminLLMConfigView.vue
git commit -m "feat: add dirty tracking to AdminLLMConfigView"
```

---

### Task 7: Integrate into AdminGlobalMailView (multi-form)

**Files:**
- Modify: `frontend/src/modules/providers/email-global/AdminGlobalMailView.vue`

This view has two independent forms: `connectionForm` and `settingsForm`. Each gets its own `useDirtyTracking` with `guard: false`, plus a shared `useDirtyGuard`.

- [ ] **Step 1: Add imports**

At line 233, after `import { ref, computed, onMounted } from 'vue'`, add:
```typescript
import { useDirtyTracking, useDirtyGuard } from '@/composables/useDirtyTracking'
```

- [ ] **Step 2: Initialize dirty tracking for both forms**

After `settingsForm` ref (after line 271), add:
```typescript
const { isDirty: connectionDirty, reset: resetConnection } = useDirtyTracking(connectionForm, { guard: false })
const { isDirty: settingsDirty, reset: resetSettings } = useDirtyTracking(settingsForm, { guard: false })
useDirtyGuard(connectionDirty, settingsDirty)
```

- [ ] **Step 3: Call resets after fetch**

In `fetchSettings()`, inside the `try` block, after `idleSupported.value = res.data.idle_supported ?? null` (after line 296), add:
```typescript
      resetConnection()
      resetSettings()
```

Note: Inside the `if (res.data)` block, after both forms have been populated.

- [ ] **Step 4: Call resetConnection after connection save**

In `handleSaveConnection()`, inside the `try` block, after `await fetchFolders()` (after line 339), add:
```typescript
    resetConnection()
```

- [ ] **Step 5: Call resetSettings after settings save**

In `handleSaveSettings()`, inside the `try` block, after `settingsSaveSuccess.value = true` (after line 362), add:
```typescript
    resetSettings()
```

- [ ] **Step 6: Update connection save button**

At line 121, change:
```html
                :disabled="savingConnection"
```
to:
```html
                :disabled="savingConnection || !connectionDirty"
```

- [ ] **Step 7: Update settings save button**

At line 219, change:
```html
                :disabled="savingSettings || loadingFolders"
```
to:
```html
                :disabled="savingSettings || loadingFolders || !settingsDirty"
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/modules/providers/email-global/AdminGlobalMailView.vue
git commit -m "feat: add dirty tracking to AdminGlobalMailView"
```

---

### Task 8: Integrate into UserImapAccountsView

**Files:**
- Modify: `frontend/src/modules/providers/email-user/UserImapAccountsView.vue`

Special consideration: This form has add/edit modes. `openAddForm()` calls `resetForm()` which resets to defaults. `openEditForm()` populates from an existing account. In both cases, `resetDirty()` must be called after the form is populated so the initial state of the opened form is the baseline.

- [ ] **Step 1: Add import**

Find the Vue import line in the `<script setup>` block (around line 560s) and add:
```typescript
import { useDirtyTracking } from '@/composables/useDirtyTracking'
```

- [ ] **Step 2: Initialize dirty tracking**

After the form ref (after line 588), add:
```typescript
const { isDirty, reset: resetDirty } = useDirtyTracking(form, { guard: false })
```

Note: `guard: false` because the form is a collapsible panel, not a full-page form. The user opens/closes it within the view.

- [ ] **Step 3: Call resetDirty in openAddForm**

In `openAddForm()` (line 627-630), after `showForm.value = true`, add:
```typescript
  resetDirty()
```

- [ ] **Step 4: Call resetDirty in openEditForm**

In `openEditForm()` (line 632-646), after `showForm.value = true` (after line 645), add:
```typescript
  resetDirty()
```

- [ ] **Step 5: Update save button**

At line 175, change:
```html
            :disabled="formSaving"
```
to:
```html
            :disabled="formSaving || !isDirty"
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/modules/providers/email-user/UserImapAccountsView.vue
git commit -m "feat: add dirty tracking to UserImapAccountsView"
```

---

### Task 9: Integrate into UserNotifyEmailView

**Files:**
- Modify: `frontend/src/modules/notifiers/notify-email/UserNotifyEmailView.vue`

Only the `events` form gets dirty tracking. The email form is a "send verification" action, not a save/revert pattern.

- [ ] **Step 1: Add import**

At line 189, after `import { ref, computed, onMounted } from 'vue'`, add:
```typescript
import { useDirtyTracking } from '@/composables/useDirtyTracking'
```

- [ ] **Step 2: Initialize dirty tracking**

After the `events` ref (after line 214), add:
```typescript
const { isDirty: eventsDirty, reset: resetEventsDirty } = useDirtyTracking(events)
```

- [ ] **Step 3: Call reset after fetch**

In `fetchConfig()`, inside the `try` block, after `events.value.package_delivered = eventList.includes('package_delivered')` (after line 235), add:
```typescript
    resetEventsDirty()
```

- [ ] **Step 4: Call reset after save**

In `handleSaveEvents()`, inside the `try` block, after `eventsSaveSuccess.value = true` (after line 284), add:
```typescript
    resetEventsDirty()
```

- [ ] **Step 5: Update events save button**

At line 176, change:
```html
              :disabled="savingEvents"
```
to:
```html
              :disabled="savingEvents || !eventsDirty"
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/modules/notifiers/notify-email/UserNotifyEmailView.vue
git commit -m "feat: add dirty tracking to UserNotifyEmailView events form"
```

---

### Task 10: Integrate into UserNotifyWebhookView (multi-form)

**Files:**
- Modify: `frontend/src/modules/notifiers/notify-webhook/UserNotifyWebhookView.vue`

Two independent forms: `webhookForm` and `events`. Each gets its own tracker, plus shared `useDirtyGuard`.

- [ ] **Step 1: Add imports**

At line 216, after `import { ref, computed, onMounted } from 'vue'`, add:
```typescript
import { useDirtyTracking, useDirtyGuard } from '@/composables/useDirtyTracking'
```

- [ ] **Step 2: Initialize dirty tracking**

After the `events` ref (after line 239), add:
```typescript
const { isDirty: webhookDirty, reset: resetWebhookDirty } = useDirtyTracking(webhookForm, { guard: false })
const { isDirty: eventsDirty, reset: resetEventsDirty } = useDirtyTracking(events, { guard: false })
useDirtyGuard(webhookDirty, eventsDirty)
```

- [ ] **Step 3: Call resets after fetch**

In `fetchConfig()`, inside the `try` block, after `events.value.package_delivered = eventList.includes('package_delivered')` (after line 266), add:
```typescript
    resetWebhookDirty()
    resetEventsDirty()
```

- [ ] **Step 4: Call resetWebhookDirty after webhook save**

In `handleSaveWebhook()`, inside the `try` block, after `saveSuccess.value = true` (after line 301), add:
```typescript
    resetWebhookDirty()
```

- [ ] **Step 5: Call resetEventsDirty after events save**

In `handleSaveEvents()`, inside the `try` block, after `eventsSaveSuccess.value = true` (after line 319), add:
```typescript
    resetEventsDirty()
```

- [ ] **Step 6: Update webhook save button**

At line 96, change:
```html
              :disabled="savingWebhook"
```
to:
```html
              :disabled="savingWebhook || !webhookDirty"
```

- [ ] **Step 7: Update events save button**

At line 171, change:
```html
              :disabled="savingEvents"
```
to:
```html
              :disabled="savingEvents || !eventsDirty"
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/modules/notifiers/notify-webhook/UserNotifyWebhookView.vue
git commit -m "feat: add dirty tracking to UserNotifyWebhookView"
```

---

### Task 11: Integrate into ProfileView

**Files:**
- Modify: `frontend/src/views/ProfileView.vue`

Only the password change form gets dirty tracking. The form starts empty, so the empty state is the clean baseline. After successful password change, the form is reset to empty and `resetDirty()` is called.

- [ ] **Step 1: Add import**

Find the Vue import line in the `<script setup>` block and add:
```typescript
import { useDirtyTracking } from '@/composables/useDirtyTracking'
```

- [ ] **Step 2: Initialize dirty tracking**

After the `pwForm` ref (after line 280), add:
```typescript
const { isDirty: pwDirty, reset: resetPwDirty } = useDirtyTracking(pwForm)
```

- [ ] **Step 3: Call resetPwDirty after password change**

In `handleChangePassword()`, inside the `try` block, after `pwForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' }` (after line 300), add:
```typescript
    resetPwDirty()
```

- [ ] **Step 4: Update save button**

At line 106, change:
```html
            :disabled="pwSaving"
```
to:
```html
            :disabled="pwSaving || !pwDirty"
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/ProfileView.vue
git commit -m "feat: add dirty tracking to ProfileView password form"
```

---

### Task 12: Integrate into OrderFormModal

**Files:**
- Modify: `frontend/src/components/OrderFormModal.vue`

Special considerations:
- Modal component, so `guard: false` (no route navigation involved)
- In edit mode, form is populated from props at line 319-338 synchronously during setup
- `useDirtyTracking` must be called after form population
- In create mode, the empty form defaults are the baseline

- [ ] **Step 1: Add import**

Find the Vue import line in the `<script setup>` block and add:
```typescript
import { useDirtyTracking } from '@/composables/useDirtyTracking'
```

- [ ] **Step 2: Initialize dirty tracking**

After the edit-mode form population block (after line 338, after the closing `}`), add:
```typescript
const { isDirty, reset: resetDirty } = useDirtyTracking(form, { guard: false })
```

This is placed after the conditional edit-mode population so the snapshot captures the correct initial state for both create and edit modes.

- [ ] **Step 3: Update save button**

At line 250, change:
```html
            :disabled="submitting"
```
to:
```html
            :disabled="submitting || !isDirty"
```

Note: No `resetDirty()` after save needed because the modal closes after successful submission (`emit('saved', ...)`).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/OrderFormModal.vue
git commit -m "feat: add dirty tracking to OrderFormModal"
```

---

### Task 13: Integrate into UsersView

**Files:**
- Modify: `frontend/src/views/admin/UsersView.vue`

The "Create User" form is a collapsible panel. `guard: false` since it's not a primary settings form.

- [ ] **Step 1: Add import**

Find the Vue import line in the `<script setup>` block and add:
```typescript
import { useDirtyTracking } from '@/composables/useDirtyTracking'
```

- [ ] **Step 2: Initialize dirty tracking**

After the form ref (after line 247), add:
```typescript
const { isDirty, reset: resetDirty } = useDirtyTracking(form, { guard: false })
```

- [ ] **Step 3: Call resetDirty when form is closed/reset**

In `closeForm()` (line 267-271), after `form.value = { username: '', password: '', is_admin: false }` (after line 269), add:
```typescript
  resetDirty()
```

- [ ] **Step 4: Update save button**

At line 83, change:
```html
            :disabled="formSaving"
```
to:
```html
            :disabled="formSaving || !isDirty"
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/admin/UsersView.vue
git commit -m "feat: add dirty tracking to UsersView create form"
```

---

### Task 14: Final verification

- [ ] **Step 1: Type-check**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: PASS with no errors

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 3: Lint**

Run: `cd frontend && npm run lint`
Expected: PASS (or only pre-existing warnings)

- [ ] **Step 4: Fix any issues and commit**

If any checks fail, fix the issues and commit fixes.
