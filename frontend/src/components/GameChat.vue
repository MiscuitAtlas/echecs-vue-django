<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  messages: { type: Array, required: true },
  myId: { type: Number, default: null },
  disabled: { type: Boolean, default: false },
  send: { type: Function, required: true },
})

const text = ref('')
const error = ref('')
const sending = ref(false)
const list = ref(null)

watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    if (list.value) list.value.scrollTop = list.value.scrollHeight
  },
  { immediate: true },
)

async function submit() {
  if (!text.value.trim() || sending.value) return
  sending.value = true
  error.value = ''
  try {
    await props.send(text.value)
    text.value = ''
  } catch (e) {
    error.value = e.message
  } finally {
    sending.value = false
  }
}

function time(iso) {
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <section class="chat" aria-labelledby="titre-chat">
    <h2 id="titre-chat">Discussion</h2>
    <ol ref="list" class="messages" aria-live="polite" aria-relevant="additions">
      <li v-for="message in messages" :key="message.id" :class="{ mine: message.auteur_id === myId }">
        <span class="author">{{ message.auteur }}</span>
        <time :datetime="message.envoye_le">{{ time(message.envoye_le) }}</time>
        <!-- Affiché comme du texte : du HTML tapé dans un message n'est jamais interprété. -->
        <p>{{ message.texte }}</p>
      </li>
      <li v-if="!messages.length" class="muted empty">Pas encore de message.</li>
    </ol>
    <form class="chat-form" @submit.prevent="submit">
      <label for="message" class="sr-only">Votre message</label>
      <input
        id="message"
        v-model="text"
        type="text"
        maxlength="300"
        autocomplete="off"
        :disabled="disabled"
        :placeholder="disabled ? 'Discussion fermée' : 'Écrire à votre adversaire'"
        :aria-describedby="error ? 'erreur-chat' : undefined"
      >
      <button type="submit" class="button" :disabled="disabled || sending || !text.trim()">Envoyer</button>
    </form>
    <p v-if="error" id="erreur-chat" class="field-error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
.messages {
  display: grid;
  gap: 0.5rem;
  max-height: 240px;
  margin: 0 0 0.75rem;
  padding: 0.75rem;
  overflow-y: auto;
  list-style: none;
  border: 1px solid var(--line);
  border-radius: var(--radius-small);
  background: var(--bg);
}

.messages li {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0 0.5rem;
}

.author {
  font-weight: 700;
}

.mine .author {
  color: var(--brass-strong);
}

time {
  color: var(--muted);
  font-size: 0.8rem;
  align-self: center;
}

.messages p {
  grid-column: 1 / -1;
  margin: 0;
  overflow-wrap: anywhere;
}

.empty {
  display: block !important;
}

.chat-form {
  display: flex;
  gap: 0.5rem;
}

.chat-form input {
  flex: 1;
  min-width: 0;
}
</style>
