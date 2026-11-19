<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { safeReturn } from '../router.js'
import { login, playAsGuest, session } from '../session.js'

const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function run(action) {
  busy.value = true
  error.value = ''
  try {
    await action()
    router.push(safeReturn(route.query.retour))
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="container page narrow">
    <h1>Connexion</h1>
    <p v-if="session.user?.invite" class="notice">
      Vous jouez en invité ({{ session.user.pseudo }}). En vous connectant à un compte, vous quittez ce compte invité.
    </p>
    <form class="panel" novalidate @submit.prevent="run(() => login(email, password))">
      <p v-if="error" id="erreur-connexion" class="notice error" role="alert">{{ error }}</p>
      <div class="field">
        <label for="email">Adresse email</label>
        <input id="email" v-model="email" type="email" autocomplete="email" required>
      </div>
      <div class="field">
        <label for="mot_de_passe">Mot de passe</label>
        <input id="mot_de_passe" v-model="password" type="password" autocomplete="current-password" required>
      </div>
      <button type="submit" class="button wide" :disabled="busy">Se connecter</button>
    </form>
    <p class="alternatives">
      Pas encore de compte ? <RouterLink to="/inscription">Créer un compte</RouterLink>
      <template v-if="!session.user">
        ou <button type="button" class="link-button" :disabled="busy" @click="run(playAsGuest)">jouer sans compte</button>.
      </template>
    </p>
  </div>
</template>

<style scoped>
.alternatives {
  margin-top: 1.25rem;
  color: var(--muted);
}
</style>
