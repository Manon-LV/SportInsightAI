import { createApp } from 'vue'
import { Quasar, Notify } from 'quasar'
import '@quasar/extras/material-icons/material-icons.css'
import 'quasar/dist/quasar.css'
import './styles/app.scss'
import App from './App.vue'

createApp(App)
  .use(Quasar, {
    plugins: { Notify },
    config: { dark: false }
  })
  .mount('#app')
