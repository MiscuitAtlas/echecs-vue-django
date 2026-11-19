<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'
import { deleteAccount, logout, session } from '../session.js'

const router = useRouter()
const passwords = reactive({ actuel: '', nouveau: '' })
const passwordErrors = ref({})
const passwordMessage = ref('')
const deletion = reactive({ open: false, password: '', error: '' })
const error = ref('')

async function changePassword() {
  passwordErrors.value = {}
  passwordMessage.value = ''
  try {
    const data = await api('compte/mot-de-passe', { method: 'POST', body: passwords })
    passwordMessage.value = data.message
    passwords.actuel = ''
    passwords.nouveau = ''
  } catch (e) {
    passwordErrors.value = e.fields || { nouveau: e.message }
  }
}

async function signOut() {
  try {
    await logout()
    router.push('/')
  } catch (e) {
    error.value = e.message
  }
}

async function remove() {
  deletion.error = ''
  try {
    await deleteAccount(deletion.password)
    router.push('/')
  } catch (e) {
    deletion.error = e.fields?.mot_de_passe || e.message
  }
}
</script>

<template>
  <div class="container page narrow">
    <h1>Mon compte</h1>
    <p v-if="error" class="notice error" role="alert">{{ error }}</p>

    <section class="panel block" aria-labelledby="titre-profil">
      <h2 id="titre-profil">{{ session.user.pseudo }}</h2>
      <template v-if="session.user.invite">
        <p>
          Vous jouez en invité : ce compte n'existe que sur ce navigateur et disparaît à la déconnexion,
          ou après deux jours sans partie.
        </p>
        <RouterLink to="/inscription" class="button">Créer mon compte et garder mes parties</RouterLink>
      </template>
      <p v-else class="muted">{{ session.user.email }}</p>
      <button type="button" class="button secondary" @click="signOut">Se déconnecter</button>
    </section>

    <section v-if="!session.user.invite" class="panel block" aria-labelledby="titre-mdp">
      <h2 id="titre-mdp">Changer de mot de passe</h2>
      <p class="help">Vos autres sessions ouvertes seront déconnectées.</p>
      <form novalidate @submit.prevent="changePassword">
        <div class="field">
          <label for="actuel">Mot de passe actuel</label>
          <input
            id="actuel"
            v-model="passwords.actuel"
            type="password"
            autocomplete="current-password"
            :aria-invalid="passwordErrors.actuel ? 'true' : undefined"
            aria-describedby="erreur-actuel"
          >
          <p v-if="passwordErrors.actuel" id="erreur-actuel" class="field-error">{{ passwordErrors.actuel }}</p>
        </div>
        <div class="field">
          <label for="nouveau">Nouveau mot de passe</label>
          <input
            id="nouveau"
            v-model="passwords.nouveau"
            type="password"
            autocomplete="new-password"
            :aria-invalid="passwordErrors.nouveau ? 'true' : undefined"
            aria-describedby="erreur-nouveau"
          >
          <p v-if="passwordErrors.nouveau" id="erreur-nouveau" class="field-error">{{ passwordErrors.nouveau }}</p>
        </div>
        <p v-if="passwordMessage" class="notice success" role="status">{{ passwordMessage }}</p>
        <button type="submit" class="button">Changer le mot de passe</button>
      </form>
    </section>

    <section class="panel block danger-zone" aria-labelledby="titre-suppression">
      <h2 id="titre-suppression">Supprimer mon compte</h2>
      <p>Vos parties en cours sont perdues par abandon. Vos adversaires gardent l'historique des parties, sous le nom « Compte supprimé ».</p>
      <button v-if="!deletion.open" type="button" class="button danger" @click="deletion.open = true">Supprimer mon compte</button>
      <form v-else novalidate @submit.prevent="remove">
        <div v-if="!session.user.invite" class="field">
          <label for="mdp-suppression">Mot de passe, pour confirmer</label>
          <input
            id="mdp-suppression"
            v-model="deletion.password"
            type="password"
            autocomplete="current-password"
            :aria-invalid="deletion.error ? 'true' : undefined"
            aria-describedby="erreur-suppression"
          >
        </div>
        <p v-if="deletion.error" id="erreur-suppression" class="field-error">{{ deletion.error }}</p>
        <div class="buttons">
          <button type="submit" class="button danger">Supprimer définitivement</button>
          <button type="button" class="button secondary" @click="deletion.open = false">Garder mon compte</button>
        </div>
      </form>
    </section>
  </div>
</template>

<style scoped>
.block {
  display: grid;
  gap: 0.75rem;
  justify-items: start;
  margin-bottom: 1.25rem;
}

.block form {
  justify-self: stretch;
}

.block p {
  margin: 0;
}

.buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-top: 0.75rem;
}
</style>
