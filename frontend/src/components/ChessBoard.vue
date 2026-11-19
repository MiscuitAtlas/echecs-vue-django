<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { colorOf, displayOrder, FILES, isLightSquare, parseFen, pieceLabel, squareIndex, squareName } from '../chess/board.js'
import PieceIcon from './PieceIcon.vue'

const props = defineProps({
  fen: { type: String, required: true },
  orientation: { type: String, default: 'w' },
  // Coups autorisés (« e2e4 », « e7e8q ») : vide quand ce n'est pas au joueur de jouer.
  legalMoves: { type: Array, default: () => [] },
  lastMove: { type: String, default: null },
  checkSquare: { type: String, default: null },
  label: { type: String, default: 'Échiquier' },
})
const emit = defineEmits(['move'])

const board = computed(() => parseFen(props.fen))
const order = computed(() => displayOrder(props.orientation))
const selected = ref(null)
const promotion = ref(null)
const focusPosition = ref(56)
const squareButtons = ref([])
const promotionButtons = ref([])

const movesFrom = computed(() => {
  const map = new Map()
  for (const uci of props.legalMoves) {
    const from = squareIndex(uci.slice(0, 2))
    if (!map.has(from)) map.set(from, [])
    map.get(from).push(uci)
  }
  return map
})
const targets = computed(() => {
  if (selected.value === null) return new Set()
  return new Set((movesFrom.value.get(selected.value) || []).map((uci) => squareIndex(uci.slice(2, 4))))
})
const lastSquares = computed(() =>
  props.lastMove ? [squareIndex(props.lastMove.slice(0, 2)), squareIndex(props.lastMove.slice(2, 4))] : [],
)

// Nouvelle position : la sélection en cours n'a plus de sens.
watch(
  () => props.fen,
  () => {
    selected.value = null
    promotion.value = null
  },
)

function describe(square) {
  const piece = board.value[square]
  let text = `${squareName(square)}, ${piece ? pieceLabel(piece) : 'vide'}`
  if (targets.value.has(square)) text += piece ? ', prise possible' : ', coup possible'
  if (selected.value === square) text += ', sélectionnée'
  return text
}

function activate(square) {
  if (promotion.value) return
  if (selected.value !== null && targets.value.has(square)) {
    play(selected.value, square)
    return
  }
  if (selected.value === square) {
    selected.value = null
  } else {
    selected.value = movesFrom.value.has(square) ? square : null
  }
}

function play(from, to) {
  const candidates = (movesFrom.value.get(from) || []).filter((uci) => squareIndex(uci.slice(2, 4)) === to)
  if (candidates.length === 0) return
  if (candidates.length > 1) {
    promotion.value = { from, to, color: colorOf(board.value[from]) }
    nextTick(() => promotionButtons.value[0]?.focus())
    return
  }
  selected.value = null
  emit('move', candidates[0])
}

function promote(kind) {
  const { from, to } = promotion.value
  promotion.value = null
  selected.value = null
  emit('move', squareName(from) + squareName(to) + kind)
}

function cancelPromotion() {
  promotion.value = null
  nextTick(() => squareButtons.value[focusPosition.value]?.focus())
}

// --- Clavier : les flèches déplacent le focus d'une case à l'autre --------------------------

function onKeydown(event, position) {
  const moves = { ArrowUp: -8, ArrowDown: 8, ArrowLeft: -1, ArrowRight: 1 }
  if (event.key in moves) {
    event.preventDefault()
    const next = position + moves[event.key]
    const sameRow = Math.floor(next / 8) === Math.floor(position / 8)
    if (next >= 0 && next < 64 && (Math.abs(moves[event.key]) === 8 || sameRow)) {
      focusPosition.value = next
      squareButtons.value[next]?.focus()
    }
  } else if (event.key === 'Escape') {
    selected.value = null
  }
}

// --- Glisser-déposer à la souris ou au doigt ------------------------------------------------

const drag = ref(null)
let suppressClick = false

function onPointerDown(event, square) {
  if (event.button !== 0 || !movesFrom.value.has(square) || promotion.value) return
  drag.value = { from: square, startX: event.clientX, startY: event.clientY, x: 0, y: 0, moving: false }
  event.currentTarget.setPointerCapture(event.pointerId)
}

function onPointerMove(event) {
  const current = drag.value
  if (!current) return
  if (!current.moving && Math.hypot(event.clientX - current.startX, event.clientY - current.startY) > 6) {
    current.moving = true
    selected.value = current.from
  }
  if (current.moving) {
    const rect = event.currentTarget.closest('.board').getBoundingClientRect()
    current.x = event.clientX - rect.left
    current.y = event.clientY - rect.top
  }
}

function onPointerUp(event) {
  const current = drag.value
  drag.value = null
  if (!current?.moving) return
  // Le clic qui suit le dépôt de la pièce ne doit pas la resélectionner.
  suppressClick = true
  setTimeout(() => {
    suppressClick = false
  }, 0)
  const element = document.elementFromPoint(event.clientX, event.clientY)?.closest('[data-square]')
  const target = element ? Number(element.dataset.square) : null
  if (target !== null && targets.value.has(target)) {
    play(current.from, target)
  }
}

function onClick(square, position) {
  focusPosition.value = position
  if (suppressClick) {
    suppressClick = false
    return
  }
  activate(square)
}

const ghostStyle = computed(() =>
  drag.value?.moving ? { transform: `translate(${drag.value.x}px, ${drag.value.y}px)` } : {},
)
</script>

<template>
  <div class="board-frame">
    <div class="board" role="group" :aria-label="label" :class="{ dragging: drag?.moving }">
      <button
        v-for="(square, position) in order"
        :key="square"
        ref="squareButtons"
        type="button"
        class="square"
        :class="{
          light: isLightSquare(square),
          dark: !isLightSquare(square),
          last: lastSquares.includes(square),
          selected: selected === square,
          target: targets.has(square) && !board[square],
          capture: targets.has(square) && board[square],
          check: checkSquare === squareName(square),
          movable: movesFrom.has(square),
          lifted: drag?.moving && drag.from === square,
        }"
        :data-square="square"
        :tabindex="position === focusPosition ? 0 : -1"
        :aria-label="describe(square)"
        :aria-pressed="movesFrom.has(square) ? selected === square : undefined"
        @click="onClick(square, position)"
        @keydown="onKeydown($event, position)"
        @pointerdown="onPointerDown($event, square)"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="drag = null"
      >
        <PieceIcon v-if="board[square]" :piece="board[square]" />
        <span v-if="position % 8 === 0" class="coord rank" aria-hidden="true">{{ Math.floor(square / 8) + 1 }}</span>
        <span v-if="position >= 56" class="coord file" aria-hidden="true">{{ FILES[square % 8] }}</span>
      </button>

      <div v-if="drag?.moving" class="ghost" :style="ghostStyle" aria-hidden="true">
        <PieceIcon :piece="board[drag.from]" />
      </div>

      <div v-if="promotion" class="promotion" role="dialog" aria-label="Choisir la pièce de promotion">
        <p>Promotion en {{ squareName(promotion.to) }}</p>
        <div class="promotion-choices">
          <button
            v-for="kind in ['q', 'r', 'b', 'n']"
            :key="kind"
            ref="promotionButtons"
            type="button"
            :aria-label="pieceLabel(promotion.color === 'w' ? kind.toUpperCase() : kind)"
            @click="promote(kind)"
            @keydown.esc="cancelPromotion"
          >
            <PieceIcon :piece="promotion.color === 'w' ? kind.toUpperCase() : kind" />
          </button>
        </div>
        <button type="button" class="link-button" @click="cancelPromotion">Annuler</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.board-frame {
  padding: clamp(6px, 1.4vw, 12px);
  border-radius: var(--radius);
  background: #0f171d;
  box-shadow: 0 18px 40px -20px rgb(0 0 0 / 70%);
}

.board {
  position: relative;
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  grid-template-rows: repeat(8, 1fr);
  aspect-ratio: 1;
  user-select: none;
  overflow: hidden;
  border-radius: 4px;
}

.square {
  position: relative;
  min-width: 0;
  min-height: 0;
  display: grid;
  place-items: center;
  margin: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: var(--square-light);
  cursor: default;
}

.square.dark {
  background: var(--square-dark);
}

.square.last {
  background-image: linear-gradient(rgb(232 183 90 / 45%), rgb(232 183 90 / 45%));
}

.square.selected {
  background-image: linear-gradient(rgb(232 183 90 / 80%), rgb(232 183 90 / 80%));
}

.square.check {
  background-image: radial-gradient(circle, rgb(233 76 52 / 95%) 0%, rgb(233 76 52 / 55%) 40%, transparent 72%);
}

.square.movable {
  cursor: grab;
  touch-action: none;
}

.dragging .square {
  cursor: grabbing;
}

.square.target::after {
  content: "";
  width: 30%;
  height: 30%;
  border-radius: 50%;
  background: rgb(23 33 41 / 45%);
}

.square.capture::after {
  content: "";
  position: absolute;
  inset: 5%;
  border: 0.35rem solid rgb(23 33 41 / 45%);
  border-radius: 50%;
}

.square.target,
.square.capture {
  cursor: pointer;
}

.square:focus-visible {
  z-index: 1;
  outline: 3px solid #fff;
  outline-offset: -3px;
}

.square :deep(.piece) {
  width: 88%;
  height: 88%;
  pointer-events: none;
}

.square.lifted :deep(.piece) {
  opacity: 0.3;
}

.coord {
  position: absolute;
  font-size: clamp(0.55rem, 1.4vw, 0.75rem);
  font-weight: 700;
  line-height: 1;
  pointer-events: none;
}

.coord.rank {
  top: 4%;
  left: 5%;
}

.coord.file {
  right: 5%;
  bottom: 4%;
}

.light .coord {
  color: var(--square-dark);
}

.dark .coord {
  color: var(--square-light);
}

.ghost {
  position: absolute;
  top: 0;
  left: 0;
  width: 12.5%;
  height: 12.5%;
  margin: -6.25% 0 0 -6.25%;
  pointer-events: none;
  z-index: 2;
}

.ghost :deep(.piece) {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 6px 6px rgb(0 0 0 / 45%));
}

.promotion {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: grid;
  place-content: center;
  gap: 0.75rem;
  padding: 1rem;
  background: rgb(15 23 29 / 82%);
  text-align: center;
}

.promotion p {
  margin: 0;
  font-family: var(--display);
  font-size: 1.2rem;
  font-weight: 700;
}

.promotion-choices {
  display: flex;
  gap: 0.5rem;
}

.promotion-choices button {
  width: clamp(48px, 11vw, 76px);
  aspect-ratio: 1;
  padding: 4px;
  border: 2px solid var(--line);
  border-radius: var(--radius-small);
  background: var(--square-light);
  cursor: pointer;
}

.promotion-choices button:hover,
.promotion-choices button:focus-visible {
  border-color: var(--brass);
}

.promotion-choices :deep(.piece) {
  width: 100%;
  height: 100%;
}
</style>
