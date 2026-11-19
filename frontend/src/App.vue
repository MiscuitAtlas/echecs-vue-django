<script setup>
import { useRouter } from 'vue-router'
import { session } from './session.js'

const router = useRouter()
</script>

<template>
  <a class="skip-link" href="#contenu">Aller au contenu</a>
  <header class="site-header">
    <div class="container header-inner">
      <RouterLink to="/" class="wordmark" aria-label="Roque, accueil">
        <svg viewBox="0 0 32 32" aria-hidden="true"><path d="M8 7h3v3h3V7h4v3h3V7h3v6l-3 3v7h3v3H8v-3h3v-7l-3-3z" /></svg>
        Roque
      </RouterLink>
      <nav aria-label="Navigation principale">
        <template v-if="session.user">
          <RouterLink to="/parties">Mes parties</RouterLink>
          <RouterLink to="/compte" class="account-link">
            {{ session.user.pseudo }}<span v-if="session.user.invite" class="badge">invité</span>
          </RouterLink>
        </template>
        <template v-else>
          <RouterLink to="/connexion">Se connecter</RouterLink>
          <RouterLink to="/inscription" class="button secondary small">Créer un compte</RouterLink>
        </template>
      </nav>
    </div>
  </header>

  <main id="contenu" tabindex="-1">
    <RouterView :key="router.currentRoute.value.path" />
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>
        Projet de licence professionnelle de Maxence Français et Théo Defossez.
        Pièces <a href="https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces/Standard">Cburnett</a>,
        licence <a href="https://creativecommons.org/licenses/by-sa/3.0/deed.fr">CC BY-SA 3.0</a>.
      </p>
    </div>
  </footer>
</template>

<style>
#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

main {
  flex: 1 0 auto;
}

main:focus {
  outline: none;
}

.skip-link {
  position: absolute;
  left: 1rem;
  top: -4rem;
  z-index: 10;
  padding: 0.6rem 1rem;
  background: var(--brass);
  color: var(--brass-ink);
  font-weight: 700;
}

.skip-link:focus {
  top: 1rem;
}

.site-header {
  border-bottom: 1px solid var(--line);
}

.header-inner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem 1.5rem;
  padding-block: 0.8rem;
}

.wordmark {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text);
  font-family: var(--display);
  font-size: 1.6rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  text-decoration: none;
}

.wordmark svg {
  width: 1.6rem;
  height: 1.6rem;
  fill: var(--brass);
}

.site-header nav {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1.25rem;
}

.site-header nav a:not(.button) {
  color: var(--text);
  font-weight: 700;
  text-decoration: none;
}

.site-header nav a:not(.button):hover,
.site-header nav a.router-link-active:not(.button) {
  color: var(--brass-strong);
}

.button.small {
  min-height: 38px;
  padding: 0.35rem 0.85rem;
}

.badge {
  margin-left: 0.4rem;
  padding: 0.05rem 0.45rem;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  font-size: 0.8rem;
  font-weight: 400;
}

.site-footer {
  margin-top: 2rem;
  padding-block: 1.25rem;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 0.9rem;
}

.site-footer p {
  margin: 0;
}

.site-footer a {
  color: var(--muted);
}
</style>
