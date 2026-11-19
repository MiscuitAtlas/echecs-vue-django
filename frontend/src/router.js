import { createRouter, createWebHistory } from 'vue-router'
import { session } from './session.js'
import HomeView from './views/HomeView.vue'

const routes = [
  { path: '/', component: HomeView, meta: { title: 'Échecs en ligne entre amis' } },
  { path: '/connexion', component: () => import('./views/LoginView.vue'), meta: { title: 'Connexion', guestOnly: true } },
  { path: '/inscription', component: () => import('./views/RegisterView.vue'), meta: { title: 'Créer un compte' } },
  { path: '/parties', component: () => import('./views/GamesView.vue'), meta: { title: 'Mes parties', auth: true } },
  { path: '/parties/:code', component: () => import('./views/GameView.vue'), meta: { title: 'Partie' } },
  { path: '/compte', component: () => import('./views/AccountView.vue'), meta: { title: 'Mon compte', auth: true } },
  { path: '/:chemin(.*)*', component: () => import('./views/NotFoundView.vue'), meta: { title: 'Page introuvable' } },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  if (to.meta.auth && !session.user) {
    return { path: '/connexion', query: { retour: to.fullPath } }
  }
  // Un vrai compte n'a rien à faire sur la page de connexion ; un invité peut s'y connecter.
  if (to.meta.guestOnly && session.user && !session.user.invite) {
    return '/parties'
  }
  return true
})

router.afterEach((to) => {
  document.title = `${to.meta.title} · Roque`
})

/** Adresse de retour après connexion : seulement une page du site. */
export function safeReturn(value) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : '/parties'
}
