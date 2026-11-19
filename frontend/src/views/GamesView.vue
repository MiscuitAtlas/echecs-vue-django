<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'
import { session } from '../session.js'

const router = useRouter()
const games = ref(null)
const color = ref('hasard')
const code = ref('')
const error = ref('')
const joinError = ref('')
const busy = ref(false)

const COLORS = [
  { value: 'w', label: 'Blancs' },
  { value: 'hasard', label: 'Au hasard' },
  { value: 'b', label: 'Noirs' },
]

async function load() {
  try {
    games.value = await api('parties')
  } catch (e) {
    error.value = e.message
  }
}
onMounted(load)

async function create() {
  busy.value = true
  error.value = ''
  try {
    const { partie } = await api('parties', { method: 'POST', body: { couleur: color.value } })
    router.push(`/parties/${partie.code}`)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

function join() {
  const clean = code.value.toUpperCase().replace(/[^A-Z0-9]/g, '')
  if (clean.length !== 6) {
    joinError.value = 'Le code compte 6 caractères, lettres et chiffres.'
    return
  }
  joinError.value = ''
  router.push(`/parties/${clean}`)
}

async function cancel(game) {
  try {
    await api(`parties/${game.code}`, { method: 'DELETE' })
    await load()
  } catch (e) {
    error.value = e.message
  }
}

function colorName(value) {
  return value === 'w' ? 'Blancs' : 'Noirs'
}

function outcome(game) {
  if (game.resultat === '1/2-1/2') return 'Nulle'
  const won = (game.resultat === '1-0') === (game.ma_couleur === 'w')
  return won ? 'Gagnée' : 'Perdue'
}

function date(iso) {
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })
}
</script>

<template>
  <div class="container page">
    <h1>Mes parties</h1>
    <p v-if="session.user?.invite" class="notice">
      Vous jouez en invité. <RouterLink to="/inscription">Créez un compte</RouterLink> pour retrouver vos parties sur un autre appareil.
    </p>
    <p v-if="error" class="notice error" role="alert">{{ error }}</p>

    <div class="start">
      <form class="panel" @submit.prevent="create">
        <h2>Nouvelle partie</h2>
        <fieldset class="colors">
          <legend>Votre couleur</legend>
          <label v-for="option in COLORS" :key="option.value" :class="{ checked: color === option.value }">
            <input v-model="color" type="radio" name="couleur" :value="option.value">
            {{ option.label }}
          </label>
        </fieldset>
        <button type="submit" class="button wide" :disabled="busy">Créer la partie</button>
        <p class="help">Vous recevrez un code à envoyer à votre adversaire.</p>
      </form>

      <form class="panel" novalidate @submit.prevent="join">
        <h2>Rejoindre une partie</h2>
        <div class="field">
          <label for="code">Code reçu</label>
          <input
            id="code"
            v-model="code"
            type="text"
            class="code-input"
            maxlength="7"
            autocomplete="off"
            autocapitalize="characters"
            spellcheck="false"
            placeholder="K7Q2XA"
            :aria-invalid="joinError ? 'true' : undefined"
            aria-describedby="erreur-code"
          >
          <p v-if="joinError" id="erreur-code" class="field-error">{{ joinError }}</p>
        </div>
        <button type="submit" class="button secondary wide">Rejoindre</button>
      </form>
    </div>

    <template v-if="games">
      <section class="list" aria-labelledby="titre-en-cours">
        <h2 id="titre-en-cours">En cours</h2>
        <ul v-if="games.en_cours.length" class="games">
          <li v-for="game in games.en_cours" :key="game.code">
            <RouterLink :to="`/parties/${game.code}`" class="game-card" :class="{ 'my-turn': game.a_moi_de_jouer }">
              <span class="opponent">contre {{ game.adversaire }}</span>
              <span class="meta">Vous avez les {{ colorName(game.ma_couleur) }}, coup {{ Math.floor(game.nb_coups / 2) + 1 }}</span>
              <span class="status">{{ game.a_moi_de_jouer ? 'À vous de jouer' : 'Au tour de votre adversaire' }}</span>
            </RouterLink>
          </li>
        </ul>
        <p v-else class="muted">Aucune partie en cours.</p>
      </section>

      <section v-if="games.en_attente.length" class="list" aria-labelledby="titre-attente">
        <h2 id="titre-attente">En attente d'un adversaire</h2>
        <ul class="games">
          <li v-for="game in games.en_attente" :key="game.code" class="waiting">
            <RouterLink :to="`/parties/${game.code}`" class="game-card">
              <span class="code">{{ game.code }}</span>
              <span class="meta">Vous avez les {{ colorName(game.ma_couleur) }}</span>
            </RouterLink>
            <button type="button" class="link-button" @click="cancel(game)">Annuler la partie {{ game.code }}</button>
          </li>
        </ul>
      </section>

      <section class="list" aria-labelledby="titre-terminees">
        <h2 id="titre-terminees">Terminées</h2>
        <ul v-if="games.terminees.length" class="games">
          <li v-for="game in games.terminees" :key="game.code">
            <RouterLink :to="`/parties/${game.code}`" class="game-card finished">
              <span class="opponent">contre {{ game.adversaire }}</span>
              <span class="meta">{{ game.raison_texte }}, le {{ date(game.maj_le) }}</span>
              <span class="status" :class="outcome(game).toLowerCase()">{{ outcome(game) }}</span>
            </RouterLink>
          </li>
        </ul>
        <p v-else class="muted">Vos parties terminées s'afficheront ici.</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.start {
  display: grid;
  gap: 1rem;
  margin-bottom: 2.5rem;
}

@media (min-width: 760px) {
  .start {
    grid-template-columns: 1fr 1fr;
  }
}

.colors {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin: 0 0 1rem;
  padding: 0;
  border: 0;
}

.colors legend {
  margin-bottom: 0.5rem;
  font-weight: 700;
}

.colors label {
  display: grid;
  place-items: center;
  min-height: 48px;
  padding: 0.4rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-small);
  font-weight: 700;
  text-align: center;
  cursor: pointer;
}

.colors label.checked {
  border-color: var(--brass);
  background: rgb(232 183 90 / 14%);
  color: var(--brass-strong);
}

.colors label:has(input:focus-visible) {
  outline: 3px solid var(--brass-strong);
  outline-offset: 2px;
}

.colors input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.code-input {
  font-family: var(--display);
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: 0.25em;
  text-transform: uppercase;
}

.list {
  margin-bottom: 2rem;
}

.games {
  display: grid;
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

@media (min-width: 760px) {
  .games {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

.game-card {
  display: grid;
  gap: 0.15rem;
  padding: 1rem 1.1rem;
  border: 1px solid var(--line);
  border-left: 4px solid var(--line);
  border-radius: var(--radius-small);
  background: var(--panel);
  color: var(--text);
  text-decoration: none;
}

.game-card:hover {
  border-color: var(--brass);
  color: var(--text);
}

.game-card.my-turn {
  border-left-color: var(--brass);
}

.opponent {
  font-weight: 700;
}

.meta {
  color: var(--muted);
  font-size: 0.92rem;
}

.status {
  margin-top: 0.3rem;
  font-weight: 700;
}

.my-turn .status,
.status.gagnée {
  color: var(--brass-strong);
}

.status.perdue {
  color: var(--danger);
}

.code {
  font-family: var(--display);
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: 0.18em;
}

.waiting {
  display: grid;
  gap: 0.4rem;
  justify-items: start;
}

.waiting .game-card {
  justify-self: stretch;
}
</style>
