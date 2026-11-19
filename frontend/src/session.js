import { reactive } from 'vue'
import { api, setCsrfToken } from './api.js'

// Joueur connecté, partagé par toutes les pages.
export const session = reactive({ user: null, loaded: false })

function apply(data) {
  session.user = data.utilisateur
  session.loaded = true
  setCsrfToken(data.csrf)
  return data
}

export async function loadSession() {
  return apply(await api('session'))
}

export async function login(email, password) {
  return apply(await api('connexion', { method: 'POST', body: { email, mot_de_passe: password } }))
}

export async function register(pseudo, email, password) {
  return apply(await api('inscription', { method: 'POST', body: { pseudo, email, mot_de_passe: password } }))
}

export async function playAsGuest() {
  return apply(await api('invite', { method: 'POST' }))
}

export async function logout() {
  return apply(await api('deconnexion', { method: 'POST' }))
}

export async function deleteAccount(password) {
  return apply(await api('compte/suppression', { method: 'POST', body: { mot_de_passe: password } }))
}
