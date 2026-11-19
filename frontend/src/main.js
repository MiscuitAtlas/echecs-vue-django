import { createApp } from 'vue'
import '@fontsource/bricolage-grotesque/700.css'
import '@fontsource/bricolage-grotesque/800.css'
import '@fontsource/atkinson-hyperlegible-next/400.css'
import '@fontsource/atkinson-hyperlegible-next/700.css'
import './styles/main.css'
import App from './App.vue'
import { router } from './router.js'
import { loadSession } from './session.js'

loadSession()
  .catch(() => {})
  .finally(() => createApp(App).use(router).mount('#app'))
