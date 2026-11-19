// Lecture de la position (FEN) et petits calculs d'affichage. Les règles elles-mêmes sont
// vérifiées par le serveur : il envoie la liste des coups possibles pour le joueur qui a le trait.

export const FILES = 'abcdefgh'

export function squareName(index) {
  return FILES[index % 8] + (Math.floor(index / 8) + 1)
}

export function squareIndex(name) {
  return (Number(name[1]) - 1) * 8 + FILES.indexOf(name[0])
}

export function isLightSquare(index) {
  return (index % 8 + Math.floor(index / 8)) % 2 === 1
}

/** Tableau de 64 cases (a1 = 0, h8 = 63) : « P », « n »… ou null. */
export function parseFen(fen) {
  const board = new Array(64).fill(null)
  const rows = fen.split(' ')[0].split('/')
  rows.forEach((row, i) => {
    let file = 0
    for (const char of row) {
      if (/\d/.test(char)) {
        file += Number(char)
      } else {
        board[(7 - i) * 8 + file] = char
        file += 1
      }
    }
  })
  return board
}

export function colorOf(piece) {
  return piece === piece.toUpperCase() ? 'w' : 'b'
}

/**
 * Applique un coup pour l'afficher tout de suite, avant la réponse du serveur :
 * roque, prise en passant et promotion compris.
 */
export function applyMove(board, uci) {
  const next = board.slice()
  const from = squareIndex(uci.slice(0, 2))
  const to = squareIndex(uci.slice(2, 4))
  const piece = next[from]
  if (!piece) return next
  const kind = piece.toLowerCase()
  if (kind === 'p' && from % 8 !== to % 8 && !next[to]) {
    next[to + (colorOf(piece) === 'w' ? -8 : 8)] = null
  }
  if (kind === 'k' && Math.abs(to - from) === 2) {
    const [rookFrom, rookTo] = to > from ? [from + 3, from + 1] : [from - 4, from - 1]
    next[rookTo] = next[rookFrom]
    next[rookFrom] = null
  }
  next[to] = uci.length === 5 ? (colorOf(piece) === 'w' ? uci[4].toUpperCase() : uci[4]) : piece
  next[from] = null
  return next
}

const FRENCH_LETTERS = { K: 'R', Q: 'D', R: 'T', B: 'F', N: 'C' }

/** Notation française : R (roi), D (dame), T (tour), F (fou), C (cavalier). */
export function frenchSan(san) {
  return san.replace(/[KQRBN]/g, (letter) => FRENCH_LETTERS[letter])
}

export const PIECE_NAMES = {
  p: 'pion', n: 'cavalier', b: 'fou', r: 'tour', q: 'dame', k: 'roi',
}

const FEMININE = new Set(['q', 'r'])

export function pieceLabel(piece) {
  const kind = piece.toLowerCase()
  const color = colorOf(piece) === 'w' ? 'blanc' : 'noir'
  return `${PIECE_NAMES[kind]} ${color}${FEMININE.has(kind) ? (color === 'blanc' ? 'he' : 'e') : ''}`
}

/** Ordre d'affichage des cases, de haut en bas et de gauche à droite, selon le côté du joueur. */
export function displayOrder(orientation) {
  const squares = []
  for (let row = 0; row < 8; row += 1) {
    for (let col = 0; col < 8; col += 1) {
      squares.push(orientation === 'w' ? (7 - row) * 8 + col : row * 8 + (7 - col))
    }
  }
  return squares
}

export function resultText(game) {
  if (game.statut !== 'terminee') return ''
  if (game.resultat === '1/2-1/2') return `Partie nulle : ${game.raison_texte.toLowerCase()}`
  const winner = game.resultat === '1-0' ? 'Les Blancs' : 'Les Noirs'
  return `${winner} gagnent : ${game.raison_texte.toLowerCase()}`
}

/** Partie « placement » de la FEN à partir des 64 cases (le reste n'est pas utilisé à l'affichage). */
export function boardToFen(board) {
  const rows = []
  for (let rank = 7; rank >= 0; rank -= 1) {
    let row = ''
    let empty = 0
    for (let file = 0; file < 8; file += 1) {
      const piece = board[rank * 8 + file]
      if (piece) {
        row += (empty || '') + piece
        empty = 0
      } else {
        empty += 1
      }
    }
    rows.push(row + (empty || ''))
  }
  return `${rows.join('/')} w - - 0 1`
}
