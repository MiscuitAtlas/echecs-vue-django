<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { frenchSan } from '../chess/board.js'

const props = defineProps({ moves: { type: Array, required: true } })

// Une ligne par coup complet, comme sur une feuille de notation : numéro, Blancs, Noirs.
const rows = computed(() => {
  const list = []
  for (let i = 0; i < props.moves.length; i += 2) {
    list.push({
      number: i / 2 + 1,
      white: frenchSan(props.moves[i].san),
      black: props.moves[i + 1] ? frenchSan(props.moves[i + 1].san) : '',
    })
  }
  return list
})

const lastPly = computed(() => props.moves.length - 1)
const scroller = ref(null)
watch(
  () => props.moves.length,
  async () => {
    await nextTick()
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
  },
)
</script>

<template>
  <section class="moves" aria-labelledby="titre-coups">
    <h2 id="titre-coups">Coups</h2>
    <div ref="scroller" class="sheet" tabindex="0" aria-label="Feuille de notation">
      <table v-if="rows.length">
        <thead>
          <tr><th scope="col"><span class="sr-only">Coup</span></th><th scope="col">Blancs</th><th scope="col">Noirs</th></tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.number">
            <th scope="row">{{ row.number }}</th>
            <td :class="{ last: lastPly === (row.number - 1) * 2 }">{{ row.white }}</td>
            <td :class="{ last: lastPly === (row.number - 1) * 2 + 1 }">{{ row.black }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted empty">Aucun coup joué.</p>
    </div>
  </section>
</template>

<style scoped>
.sheet {
  max-height: 260px;
  overflow-y: auto;
  border: 1px solid var(--line);
  border-radius: var(--radius-small);
  background: var(--bg);
}

table {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
}

thead th {
  position: sticky;
  top: 0;
  padding: 0.35rem 0.75rem;
  background: var(--panel-2);
  color: var(--muted);
  font-size: 0.85rem;
  font-weight: 700;
  text-align: left;
}

tbody th {
  width: 3rem;
  padding: 0.3rem 0.75rem;
  color: var(--muted);
  font-weight: 400;
  text-align: right;
}

td {
  padding: 0.3rem 0.75rem;
  font-weight: 700;
}

tbody tr:nth-child(even) {
  background: rgb(255 255 255 / 3%);
}

td.last {
  color: var(--brass-strong);
}

.empty {
  margin: 0;
  padding: 0.75rem;
}
</style>
