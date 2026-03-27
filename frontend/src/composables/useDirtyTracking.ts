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
