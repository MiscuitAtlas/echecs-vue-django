import { onBeforeUnmount, ref } from 'vue'

const FORBIDDEN = 4403

/**
 * Connexion WebSocket à une partie : le serveur y envoie la nouvelle position et les messages.
 * En cas de coupure (réseau, mise en veille), elle se rétablit d'elle-même.
 */
export function useGameSocket({ onState, onMessage }) {
  const status = ref('ferme')
  let socket = null
  let retries = 0
  let timer = null
  let stopped = false

  function open(code) {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
    socket = new WebSocket(`${scheme}://${window.location.host}/ws/parties/${code}/`)
    socket.addEventListener('open', () => {
      retries = 0
      status.value = 'connecte'
    })
    socket.addEventListener('message', (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'partie') onState(data.partie)
      if (data.type === 'message') onMessage(data.message)
    })
    socket.addEventListener('close', (event) => {
      if (stopped) return
      if (event.code === FORBIDDEN) {
        status.value = 'refuse'
        return
      }
      status.value = 'coupe'
      retries += 1
      timer = setTimeout(() => open(code), Math.min(1000 * 2 ** (retries - 1), 15000))
    })
  }

  function connect(code) {
    if (socket) return
    stopped = false
    status.value = 'connexion'
    open(code)
  }

  function stop() {
    stopped = true
    clearTimeout(timer)
    socket?.close()
    socket = null
  }

  onBeforeUnmount(stop)
  return { status, connect, stop }
}
