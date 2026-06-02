<template>
  <q-card class="glass-panel contrast-panel report-panel" flat>
    <q-card-section class="q-py-sm">
      <div v-if="summary" class="row items-center q-col-gutter-sm">
        <div class="col-12 col-lg">
          <div class="text-subtitle2 text-weight-bold">{{ headline }}</div>
          <div class="text-caption text-blue-grey-3">{{ halfLabel }}</div>
        </div>
        <div class="col-12 col-lg-auto row q-gutter-xs items-center">
          <q-chip dense square color="green-8" text-color="white" icon="sports_soccer">
            {{ countFor('Goal') }}
          </q-chip>
          <q-chip dense square color="amber-9" text-color="black" icon="style">
            {{ cardsCount }}
          </q-chip>
          <q-chip dense square color="cyan-8" text-color="black" icon="gps_fixed">
            {{ shotsCount }}
          </q-chip>
          <q-chip dense square color="blue-grey-7" text-color="white">
            {{ events.length }} actions
          </q-chip>
          <q-chip dense square color="purple-8" text-color="white" size="xs">
            {{ summary.run_id }}
          </q-chip>
        </div>
      </div>
      <div v-else class="text-caption text-blue-grey-3">
        Lance une analyse pour afficher le résumé.
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { EventPrediction, RunSummary } from '../types/predictions'

const props = defineProps<{
  summary: RunSummary | null
  events: EventPrediction[]
}>()

function countFor(label: string): number {
  return props.events.filter((e) => e.label === label).length
}

const cardsCount = computed(() => countFor('Yellow card') + countFor('Red card'))
const shotsCount = computed(() => countFor('Shots on target') + countFor('Shots off target'))

const halfLabel = computed(() => {
  if (!props.summary) return ''
  const match = props.summary.match_dir.split(/[\\/]/).at(-1) ?? ''
  const half =
    props.summary.half === 'both' ? 'Match complet' :
    props.summary.half === 'first' ? '1re mi-temps' : '2e mi-temps'
  return `${half} · ${match}`
})

const headline = computed(() => {
  if (!props.summary) return ''
  const g = countFor('Goal')
  const c = cardsCount.value
  const s = shotsCount.value
  return `${props.events.length} actions · ${g} but${g > 1 ? 's' : ''} · ${c} carton${c > 1 ? 's' : ''} · ${s} tir${s > 1 ? 's' : ''}`
})
</script>
