<template>
  <q-card class="glass-panel contrast-panel report-panel" flat>
    <q-card-section class="row items-center justify-between q-col-gutter-md">
      <div class="col-12 col-lg">
        <div class="text-overline text-purple-3">Résumé automatique</div>
        <div class="text-h6">{{ headline }}</div>
        <div v-if="summary" class="text-body2 text-blue-grey-1 q-mt-xs">
          Analyse {{ halfLabel }} · source : {{ summary.match_dir }}
        </div>
      </div>
      <div class="col-12 col-lg-auto">
        <q-chip v-if="summary" square color="purple-5" text-color="white">{{ summary.run_id }}</q-chip>
      </div>
    </q-card-section>

    <q-card-section v-if="summary" class="row q-col-gutter-md">
      <div class="col-6 col-md-3">
        <q-card flat bordered class="metric-card metric-actions">
          <q-card-section>
            <div class="text-caption">Actions</div>
            <div class="text-h4">{{ events.length }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat bordered class="metric-card metric-goal">
          <q-card-section>
            <div class="text-caption">Buts</div>
            <div class="text-h4">{{ countFor('Goal') }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat bordered class="metric-card metric-corner">
          <q-card-section>
            <div class="text-caption">Corners</div>
            <div class="text-h4">{{ countFor('Corner') }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-md-3">
        <q-card flat bordered class="metric-card metric-cards">
          <q-card-section>
            <div class="text-caption">Cartons</div>
            <div class="text-h4">{{ cardsCount }}</div>
          </q-card-section>
        </q-card>
      </div>
    </q-card-section>

    <q-card-section v-else class="text-blue-grey-2">
      Lance une analyse ou charge la démo JSON pour générer le résumé.
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
  return props.events.filter((event) => event.label === label).length
}

const cardsCount = computed(() => countFor('Yellow card') + countFor('Red card'))

const halfLabel = computed(() => {
  if (!props.summary) return ''
  if (props.summary.half === 'both') return 'du match complet'
  if (props.summary.half === 'first') return 'de la première mi-temps'
  if (props.summary.half === 'second') return 'de la deuxième mi-temps'
  return props.summary.half
})

const headline = computed(() => {
  if (!props.summary) return 'Aucun rapport généré'
  const goalCount = countFor('Goal')
  const cornerCount = countFor('Corner')
  const yellowCount = countFor('Yellow card')
  const redCount = countFor('Red card')
  return `${props.events.length} actions détectées · ${goalCount} buts · ${cornerCount} corners · ${yellowCount + redCount} cartons`
})
</script>

<style scoped>
.metric-card .text-caption {
  color: rgba(248, 250, 252, 0.78);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
</style>
