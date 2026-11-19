<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { register, session } from '../session.js'

const router = useRouter()
const form = reactive({ pseudo: '', email: '', password: '' })
const errors = ref({})
const error = ref('')
const busy = ref(false)
const wasGuest = session.user?.invite

if (session.user && !session.user.invite) router.replace('/parties')

async function submit() {
  busy.value = true
  error.value = ''
  errors.value = {}
  try {
    await register(form.pseudo, form.email, form.password)
    router.push('/parties')
  } catch (e) {
    error.value = e.message
    errors.value = e.fields || {}
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="container page narrow">
    <h1>Créer un compte</h1>
    <p v-if="wasGuest" class="notice">Vos parties jouées en invité sont conservées dans votre nouveau compte.</p>
    <form class="panel" novalidate @submit.prevent="submit">
      <p v-if="error" class="notice error" role="alert">{{ error }}</p>
      <div class="field">
        <label for="pseudo">Pseudo</label>
        <input
          id="pseudo"
          v-model="form.pseudo"
          type="text"
          autocomplete="username"
          maxlength="20"
          required
          :aria-invalid="errors.pseudo ? 'true' : undefined"
          aria-describedby="aide-pseudo erreur-pseudo"
        >
        <p id="aide-pseudo" class="help">Visible par vos adversaires. 3 à 20 caractères.</p>
        <p v-if="errors.pseudo" id="erreur-pseudo" class="field-error">{{ errors.pseudo }}</p>
      </div>
      <div class="field">
        <label for="email">Adresse email</label>
        <input
          id="email"
          v-model="form.email"
          type="email"
          autocomplete="email"
          required
          :aria-invalid="errors.email ? 'true' : undefined"
          aria-describedby="erreur-email"
        >
        <p v-if="errors.email" id="erreur-email" class="field-error">{{ errors.email }}</p>
      </div>
      <div class="field">
        <label for="mot_de_passe">Mot de passe</label>
        <input
          id="mot_de_passe"
          v-model="form.password"
          type="password"
          autocomplete="new-password"
          required
          :aria-invalid="errors.mot_de_passe ? 'true' : undefined"
          aria-describedby="aide-mdp erreur-mdp"
        >
        <p id="aide-mdp" class="help">Au moins 10 caractères, pas seulement des chiffres.</p>
        <p v-if="errors.mot_de_passe" id="erreur-mdp" class="field-error">{{ errors.mot_de_passe }}</p>
      </div>
      <button type="submit" class="button wide" :disabled="busy">Créer mon compte</button>
    </form>
    <p class="muted alternatives">Déjà inscrit ? <RouterLink to="/connexion">Se connecter</RouterLink></p>
  </div>
</template>

<style scoped>
.alternatives {
  margin-top: 1.25rem;
}
</style>
