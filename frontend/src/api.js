// Appels à l'API Django. Le jeton CSRF reçu avec la session accompagne chaque modification.

let csrfToken = ''

export class ApiError extends Error {
  constructor(message, status, fields = {}) {
    super(message)
    this.status = status
    this.fields = fields
  }
}

export function setCsrfToken(token) {
  csrfToken = token || ''
}

export async function api(path, { method = 'GET', body } = {}) {
  const options = { method, credentials: 'same-origin', headers: { Accept: 'application/json' } }
  if (method !== 'GET') {
    options.headers['Content-Type'] = 'application/json'
    options.headers['X-CSRFToken'] = csrfToken
    options.body = JSON.stringify(body ?? {})
  }
  let response
  try {
    response = await fetch(`/api/${path}`, options)
  } catch {
    throw new ApiError('Le serveur ne répond pas. Vérifiez votre connexion.', 0)
  }
  const data = await response.json().catch(() => ({}))
  if (data.csrf) setCsrfToken(data.csrf)
  if (!response.ok) {
    throw new ApiError(data.erreur || `Erreur ${response.status}`, response.status, data.champs || {})
  }
  return data
}
