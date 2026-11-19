<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'
import { applyMove, boardToFen, frenchSan, parseFen, resultText } from '../chess/board.js'
import ChessBoard from '../components/ChessBoard.vue'
import GameChat from '../components/GameChat.vue'
import MoveList from '../components/MoveList.vue'
import { useGameSocket } from '../composables/useGameSocket.js'
import { playAsGuest, session } from '../session.js'

const route = useRoute()
const router = useRouter()
const code = String(route.params.code).toUpperCase().replace(/[^A-Z0-9]/g, '')

const game = ref(null)
const invitation = ref(null)
const loadError = ref('')
const error = ref('')
const busy = ref(false)
const pendingFen = ref(null)
const announcement = ref('')
const copied = ref(false)
const confirmResign = ref(false)

const socket = useGameSocket({
  onState: (state) => receive(state),
  onMessage: (message) => {
    if (game.value && !game.value.messages.some((m) => m.id === message.id)) {
      game.value.messages.push(message)
    }
  },
})

function receive(state) {
  const previous = game.value
  game.value = state
  pendingFen.value = null
  invitation.value = null
  // Annonce pour les lecteurs d'écran : le coup de l'adversaire et la fin de partie.
  if (previous && state.coups.length > previous.coups.length) {
    const last = state.coups[state.coups.length - 1]
    const byOpponent = state.trait === state.ma_couleur
    if (byOpponent) announcement.value = `${opponent.value?.pseudo ?? 'Votre adversaire'} a joué ${frenchSan(last.san)}.`
  }
  if (previous?.statut === 'en_cours' && state.statut === 'terminee') {
    announcement.value = resultText(state)
  }
  if (state.statut === 'en_cours' && state.trait === state.ma_couleur) {
    document.title = 'À vous de jouer · Roque'
  } else {
    document.title = `Partie ${state.code} · Roque`
  }
}

async function load() {
  loadError.value = ''
  if (!session.user) return
  try {
    const data = await api(`parties/${code}`)
    if (data.partie) {
      receive(data.partie)
      socket.connect(code)
    } else {
      invitation.value = data.invitation
    }
  } catch (e) {
    loadError.value = e.message
  }
}
onMounted(load)

const me = computed(() => game.value?.ma_couleur)
const opponent = computed(() => (game.value ? game.value[me.value === 'w' ? 'noirs' : 'blancs'] : null))
const fen = computed(() => pendingFen.value ?? game.value?.fen)
const lastMove = computed(() => game.value?.coups.at(-1)?.uci ?? null)
const myTurn = computed(() => game.value?.statut === 'en_cours' && game.value.trait === me.value)
const shareUrl = computed(() => `${window.location.origin}/parties/${code}`)

const status = computed(() => {
  const g = game.value
  if (!g) return ''
  if (g.statut === 'attente') return 'En attente de votre adversaire'
  if (g.statut === 'terminee') return resultText(g)
  if (myTurn.value) return g.echec ? 'Échec ! À vous de jouer' : 'À vous de jouer'
  const name = opponent.value?.pseudo ?? 'votre adversaire'
  // « Au tour d'Invité-1234 », « Au tour de Bruno »
  return /^[aeiouyàâéèêîôû]/i.test(name) ? `Au tour d'${name}` : `Au tour de ${name}`
})

async function action(path, body) {
  busy.value = true
  error.value = ''
  try {
    const data = await api(`parties/${code}/${path}`, { method: 'POST', body })
    receive(data.partie)
  } catch (e) {
    error.value = e.message
    pendingFen.value = null
  } finally {
    busy.value = false
  }
}

function play(uci) {
  // Le coup s'affiche aussitôt ; la réponse du serveur fait foi.
  pendingFen.value = boardToFen(applyMove(parseFen(game.value.fen), uci))
  action('coups', { coup: uci, demi_coup: game.value.coups.length })
}

function resign() {
  if (!confirmResign.value) {
    confirmResign.value = true
    setTimeout(() => {
      confirmResign.value = false
    }, 5000)
    return
  }
  confirmResign.value = false
  action('abandon')
}

async function join() {
  busy.value = true
  error.value = ''
  try {
    const data = await api(`parties/${code}/rejoindre`, { method: 'POST' })
    receive(data.partie)
    socket.connect(code)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function joinAsGuest() {
  busy.value = true
  error.value = ''
  try {
    await playAsGuest()
    await load()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(shareUrl.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2500)
  } catch {
    error.value = 'Copie impossible : sélectionnez le lien à la main.'
  }
}

async function cancel() {
  try {
    await api(`parties/${code}`, { method: 'DELETE' })
    router.push('/parties')
  } catch (e) {
    error.value = e.message
  }
}

function sendMessage(text) {
  return api(`parties/${code}/messages`, { method: 'POST', body: { texte: text } }).then(({ message }) => {
    if (!game.value.messages.some((m) => m.id === message.id)) game.value.messages.push(message)
  })
}

function seatName(color) {
  const seat = game.value?.[color === 'w' ? 'blancs' : 'noirs']
  return seat ? seat.pseudo : 'En attente…'
}
</script>

<template>
  <div class="container page">
    <p class="sr-only" aria-live="polite">{{ announcement }}</p>

    <!-- Visiteur non connecté qui a reçu le lien -->
    <section v-if="!session.user" class="panel invite narrow-block">
      <h1>Invitation à une partie</h1>
      <p class="lead">Quelqu'un vous attend pour une partie d'échecs (code <strong>{{ code }}</strong>).</p>
      <p v-if="error" class="notice error" role="alert">{{ error }}</p>
      <div class="invite-actions">
        <button type="button" class="button" :disabled="busy" @click="joinAsGuest">Jouer sans compte</button>
        <RouterLink :to="{ path: '/connexion', query: { retour: route.fullPath } }" class="button secondary">Se connecter</RouterLink>
      </div>
    </section>

    <section v-else-if="loadError" class="narrow-block">
      <h1>Partie {{ code }}</h1>
      <p class="notice error" role="alert">{{ loadError }}</p>
      <RouterLink to="/parties" class="button secondary">Retour à mes parties</RouterLink>
    </section>

    <section v-else-if="invitation" class="panel invite narrow-block">
      <h1>{{ invitation.createur_pseudo }} vous invite</h1>
      <p class="lead">
        Partie {{ invitation.code }} : vous jouerez avec les {{ invitation.couleur_libre === 'w' ? 'Blancs' : 'Noirs' }}.
      </p>
      <p v-if="error" class="notice error" role="alert">{{ error }}</p>
      <button type="button" class="button" :disabled="busy" @click="join">Rejoindre la partie</button>
    </section>

    <div v-else-if="game" class="game">
      <div class="board-column">
        <p class="player top">
          <span class="dot" :class="me === 'w' ? 'black' : 'white'" aria-hidden="true" />
          <span class="name">{{ seatName(me === 'w' ? 'b' : 'w') }}</span>
          <span v-if="opponent?.invite" class="badge">invité</span>
        </p>
        <ChessBoard
          :fen="fen"
          :orientation="me"
          :legal-moves="busy || pendingFen ? [] : game.coups_possibles"
          :last-move="lastMove"
          :check-square="game.echec"
          :label="`Échiquier, vous jouez les ${me === 'w' ? 'Blancs' : 'Noirs'}`"
          @move="play"
        />
        <p class="player bottom">
          <span class="dot" :class="me === 'w' ? 'white' : 'black'" aria-hidden="true" />
          <span class="name">{{ session.user.pseudo }} (vous)</span>
        </p>
      </div>

      <aside class="side" aria-label="Déroulement de la partie">
        <div class="status panel" :class="{ 'my-turn': myTurn, over: game.statut === 'terminee', check: game.echec && game.statut === 'en_cours' }">
          <p class="game-code">Partie <span>{{ game.code }}</span></p>
          <h1 class="status-text">{{ status }}</h1>
          <p v-if="socket.status.value === 'coupe'" class="muted connection" role="status">Connexion perdue, reconnexion…</p>

          <template v-if="game.statut === 'attente'">
            <p>Envoyez ce lien ou le code <strong class="code">{{ game.code }}</strong> à votre adversaire. La partie commence dès qu'il la rejoint.</p>
            <p class="share"><input :value="shareUrl" type="text" readonly aria-label="Lien de la partie" @focus="$event.target.select()"></p>
            <div class="buttons">
              <button type="button" class="button" @click="copyLink">{{ copied ? 'Lien copié' : 'Copier le lien' }}</button>
              <button v-if="game.createur" type="button" class="button danger" @click="cancel">Annuler la partie</button>
            </div>
          </template>

          <template v-if="game.statut === 'en_cours'">
            <div v-if="game.nulle_proposee_par && game.nulle_proposee_par !== me" class="draw-offer" role="status">
              <p>{{ opponent?.pseudo }} propose la nulle.</p>
              <div class="buttons">
                <button type="button" class="button" :disabled="busy" @click="action('nulle', { action: 'accepter' })">Accepter</button>
                <button type="button" class="button secondary" :disabled="busy" @click="action('nulle', { action: 'refuser' })">Refuser</button>
              </div>
            </div>
            <p v-else-if="game.nulle_proposee_par === me" class="muted">Vous avez proposé la nulle.</p>
            <div class="buttons">
              <button
                v-if="!game.nulle_proposee_par"
                type="button"
                class="button secondary"
                :disabled="busy"
                @click="action('nulle', { action: 'proposer' })"
              >
                Proposer la nulle
              </button>
              <button type="button" class="button danger" :disabled="busy" @click="resign">
                {{ confirmResign ? 'Confirmer l\'abandon' : 'Abandonner' }}
              </button>
            </div>
          </template>

          <p v-if="error" class="notice error" role="alert">{{ error }}</p>
        </div>

        <MoveList :moves="game.coups" />
        <GameChat
          v-if="game.statut !== 'attente'"
          :messages="game.messages"
          :my-id="session.user.id"
          :send="sendMessage"
        />
      </aside>
    </div>
  </div>
</template>

<style scoped>
.narrow-block {
  max-width: 560px;
  margin-inline: auto;
}

.invite-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.game {
  display: grid;
  gap: 1.5rem;
  align-items: start;
}

@media (min-width: 980px) {
  .game {
    grid-template-columns: minmax(0, 640px) minmax(320px, 1fr);
    gap: 2rem;
  }
}

.board-column {
  width: min(100%, 640px);
}

.player {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  padding: 0.5rem 0.25rem;
  font-weight: 700;
}

.dot {
  width: 0.9rem;
  height: 0.9rem;
  border: 2px solid var(--muted);
  border-radius: 50%;
}

.dot.white {
  background: var(--square-light);
}

.dot.black {
  background: #0f171d;
}

.side {
  display: grid;
  gap: 1.25rem;
}

.status {
  border-top: 4px solid var(--line);
}

.status.my-turn {
  border-top-color: var(--brass);
}

.status.check {
  border-top-color: var(--danger);
}

.status.over {
  border-top-color: var(--ok);
}

.game-code {
  margin: 0 0 0.25rem;
  color: var(--muted);
  font-size: 0.9rem;
}

.game-code span {
  font-family: var(--display);
  font-weight: 700;
  letter-spacing: 0.12em;
}

.status-text {
  font-size: clamp(1.4rem, 3vw, 1.9rem);
  margin-bottom: 0.9rem;
}

.connection {
  margin-top: -0.5rem;
}

.code {
  font-family: var(--display);
  letter-spacing: 0.12em;
  color: var(--brass-strong);
}

.share input {
  font-size: 0.92rem;
}

.buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.draw-offer {
  margin-bottom: 1rem;
  padding: 0.75rem;
  border-radius: var(--radius-small);
  background: var(--panel-2);
}

.draw-offer p {
  margin-bottom: 0.6rem;
  font-weight: 700;
}

.status .notice {
  margin: 1rem 0 0;
}
</style>
