<script setup>
import { computed } from 'vue'
import { colorOf } from '../chess/board.js'

const props = defineProps({ piece: { type: String, required: true } })
const href = computed(() => `/pieces.svg#${colorOf(props.piece)}${props.piece.toLowerCase()}`)
</script>

<template>
  <svg class="piece" viewBox="0 0 40 40" aria-hidden="true" focusable="false"><use :href="href" /></svg>
</template>
