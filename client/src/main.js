import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from "axios"
import Cookies from "js-cookie"
import "bootstrap/dist/css/bootstrap.css"
import "bootstrap-icons/font/bootstrap-icons.min.css"
import "bootstrap/dist/js/bootstrap.bundle.min.js"

import App from './App.vue'
import router from './router'
import { useAuthStore } from "./stores/auth"

const app = createApp(App)
const pinia = createPinia()

axios.defaults.withCredentials = true
axios.defaults.headers.common["X-Requested-With"] = "XMLHttpRequest"

if (Cookies.get("csrftoken")) {
  axios.defaults.headers.common["X-CSRFToken"] = Cookies.get("csrftoken")
}

axios.interceptors.request.use((config) => {
  const csrf = Cookies.get("csrftoken")
  if (csrf) {
    config.headers["X-CSRFToken"] = csrf
  }
  return config
})

app.use(pinia)
app.use(router)

const auth = useAuthStore()
auth.initSession().finally(() => {
  app.mount('#app')
})
