<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import ChessBoard from '../components/ChessBoard.vue'
import { playAsGuest, session } from '../session.js'

const router = useRouter()
const error = ref('')
const busy = ref(false)

// Partie italienne après 3…Fc5 : la position affichée sur la page d'accueil.
const SAMPLE = 'r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4'

async function guest() {
  busy.value = true
  error.value = ''
  try {
    await playAsGuest()
    router.push('/parties')
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="container page home">
    <section class="hero" aria-labelledby="titre-accueil">
      <div class="hero-text">
        <h1 id="titre-accueil">Une partie d'échecs entre amis, avec un simple code.</h1>
        <p class="lead">
          Créez une partie, envoyez le code à votre adversaire et jouez en direct, chacun sur son écran.
          Le serveur vérifie chaque coup, du roque à l'échec et mat.
        </p>
        <p v-if="error" class="notice error" role="alert">{{ error }}</p>
        <div v-if="session.user" class="actions">
          <RouterLink to="/parties" class="button">Voir mes parties</RouterLink>
        </div>
        <div v-else class="actions">
          <button type="button" class="button" :disabled="busy" @click="guest">Jouer sans compte</button>
          <RouterLink to="/inscription" class="button secondary">Créer un compte</RouterLink>
          <RouterLink to="/connexion">Se connecter</RouterLink>
        </div>
        <p v-if="!session.user" class="help">Sans compte, vous jouez sous un pseudo d'invité, valable sur ce navigateur.</p>
      </div>
      <div class="hero-board">
        <ChessBoard :fen="SAMPLE" last-move="f8c5" label="Exemple de position : partie italienne" />
      </div>
    </section>

    <section class="steps" aria-labelledby="titre-etapes">
      <h2 id="titre-etapes">Comment jouer</h2>
      <ol>
        <li><strong>Créez une partie</strong> et choisissez les Blancs, les Noirs ou le hasard.</li>
        <li><strong>Envoyez le code</strong> ou le lien de la partie à votre adversaire.</li>
        <li><strong>Jouez</strong> : chaque coup apparaît aussitôt chez l'autre, avec la feuille de notation et la discussion.</li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.hero {
  display: grid;
  gap: 2rem;
  align-items: center;
}

@media (min-width: 900px) {
  .hero {
    grid-template-columns: 1.05fr 1fr;
    gap: 3.5rem;
    min-height: 62vh;
  }
}

.hero-board {
  width: min(100%, 520px);
  justify-self: center;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1.25rem;
  margin: 1.5rem 0 0.75rem;
}

.steps {
  margin-top: 3.5rem;
}

.steps ol {
  display: grid;
  gap: 1rem;
  margin: 1rem 0 0;
  padding: 0;
  list-style: none;
  counter-reset: step;
}

@media (min-width: 760px) {
  .steps ol {
    grid-template-columns: repeat(3, 1fr);
  }
}

.steps li {
  position: relative;
  padding: 1.25rem 1.25rem 1.25rem 4rem;
  border-top: 3px solid var(--brass);
  background: var(--panel);
  border-radius: 0 0 var(--radius) var(--radius);
  counter-increment: step;
}

.steps li::before {
  content: counter(step);
  position: absolute;
  top: 1rem;
  left: 1.25rem;
  font-family: var(--display);
  font-size: 2rem;
  font-weight: 800;
  line-height: 1;
  color: var(--brass);
}
</style>
