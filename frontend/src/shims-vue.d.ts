declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module '@/api' {
  export const translateApi: any
  export const systemApi: any
  export const literaryApi: any
}
