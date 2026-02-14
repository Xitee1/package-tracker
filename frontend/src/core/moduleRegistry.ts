import type { RouteRecordRaw } from 'vue-router'

export interface ModuleManifest {
  key: string
  name: string
  type: 'analyser' | 'provider'
  adminRoutes: { path: string; component: () => Promise<unknown>; label?: string }[]
  userRoutes?: { path: string; component: () => Promise<unknown>; label: string }[]
}

const modules: ModuleManifest[] = []

export function registerModule(manifest: ModuleManifest) {
  modules.push(manifest)
}

export function getModules(): ModuleManifest[] {
  return modules
}

export function getModulesByType(type: 'analyser' | 'provider'): ModuleManifest[] {
  return modules.filter((m) => m.type === type)
}

export function getAdminRoutes(): RouteRecordRaw[] {
  return modules.flatMap((m) =>
    m.adminRoutes.map((r) => ({
      path: r.path,
      component: r.component,
      meta: { moduleKey: m.key },
    })),
  )
}

export function getUserRoutes(): RouteRecordRaw[] {
  return modules.flatMap((m) =>
    (m.userRoutes || []).map((r) => ({
      path: r.path,
      component: r.component,
      meta: { moduleKey: m.key },
    })),
  )
}

export function getAdminSidebarItems(): {
  group: string
  items: { to: string; label: string; moduleKey: string }[]
}[] {
  const analysers = getModulesByType('analyser')
  const providers = getModulesByType('provider')

  const groups = []

  if (analysers.length > 0) {
    groups.push({
      group: 'Analysers',
      items: analysers.flatMap((m) =>
        m.adminRoutes.map((r) => ({
          to: `/admin/settings/${r.path}`,
          label: r.label || m.name,
          moduleKey: m.key,
        })),
      ),
    })
  }

  if (providers.length > 0) {
    groups.push({
      group: 'Providers',
      items: providers.flatMap((m) =>
        m.adminRoutes.map((r) => ({
          to: `/admin/settings/${r.path}`,
          label: r.label || m.name,
          moduleKey: m.key,
        })),
      ),
    })
  }

  return groups
}

export function getUserSidebarItems(): { to: string; label: string; moduleKey: string }[] {
  return modules.flatMap((m) =>
    (m.userRoutes || []).map((r) => ({
      to: `/providers/${r.path}`,
      label: r.label,
      moduleKey: m.key,
    })),
  )
}
