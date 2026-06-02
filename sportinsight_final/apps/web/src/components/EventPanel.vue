<template>
  <q-card class="glass-panel contrast-panel event-panel" flat>
    <q-card-section class="row items-center justify-between">
      <div>
        <div class="text-overline text-amber-3">Événement sélectionné</div>
        <div class="text-h6">Détail action</div>
      </div>
      <q-btn flat dense no-caps icon="list" color="amber" label="Toutes les actions" @click="dialogOpen = true" />
    </q-card-section>

    <q-separator dark />

    <q-card-section v-if="selected" class="q-gutter-md selected-card">
      <div class="row items-center q-gutter-sm">
        <q-avatar :color="colorFor(selected.label)" text-color="white" size="44px">
          {{ selected.label.slice(0, 1) }}
        </q-avatar>
        <div>
          <div class="text-h5 text-weight-bold">{{ selected.label }}</div>
          <div class="text-blue-grey-2">{{ selected.gameTime }}</div>
        </div>
      </div>

      <q-list dense dark>
        <q-item>
          <q-item-section>Mi-temps</q-item-section>
          <q-item-section side>{{ selected.half }}</q-item-section>
        </q-item>
        <q-item>
          <q-item-section>Timestamp</q-item-section>
          <q-item-section side>{{ selected.timestamp.toFixed(1) }} s</q-item-section>
        </q-item>
        <q-item>
          <q-item-section>Confiance</q-item-section>
          <q-item-section side>{{ selected.score.toFixed(3) }}</q-item-section>
        </q-item>
      </q-list>

      <VideoClipPreview :event="selected" :match-dir="matchDir" />
    </q-card-section>

    <q-card-section v-else class="text-blue-grey-2">
      Sélectionne un point sur la timeline pour afficher son détail.
    </q-card-section>

    <q-dialog v-model="dialogOpen">
      <q-card class="event-dialog text-white">
        <q-card-section class="row items-center justify-between">
          <div>
            <div class="text-overline text-amber-3">Liste complète</div>
            <div class="text-h6">{{ events.length }} actions détectées</div>
          </div>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>

        <q-separator dark />

        <q-list separator dark style="max-height: 70vh; overflow: auto">
          <q-item
            v-for="event in events"
            :key="`${event.half}-${event.timestamp}-${event.label}`"
            clickable
            v-close-popup
            @click="$emit('select', event)"
          >
            <q-item-section avatar>
              <q-avatar :color="colorFor(event.label)" text-color="white" size="34px">
                {{ event.label.slice(0, 1) }}
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ event.label }}</q-item-label>
              <q-item-label caption>{{ event.gameTime }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge color="cyan-9">{{ event.score.toFixed(2) }}</q-badge>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </q-dialog>
  </q-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import VideoClipPreview from './VideoClipPreview.vue'
import type { EventPrediction } from '../types/predictions'

defineProps<{
  events: EventPrediction[]
  selected: EventPrediction | null
  matchDir: string
}>()

defineEmits<{
  select: [event: EventPrediction]
}>()

const dialogOpen = ref(false)

const CLASS_COLORS: Record<string, string> = {
  'Goal': 'green-7',
  'Corner': 'light-blue-7',
  'Yellow card': 'amber-8',
  'Red card': 'red-7',
  'Penalty': 'orange-8',
  'Substitution': 'purple-7',
  'Offside': 'teal-6',
  'Foul': 'deep-orange-7',
  'Shots on target': 'cyan-7',
  'Shots off target': 'blue-grey-6',
}

function colorFor(label: string): string {
  return CLASS_COLORS[label] ?? 'blue-grey-7'
}
</script>

<style scoped>
.event-dialog {
  width: 620px;
  max-width: 92vw;
  background: linear-gradient(135deg, rgba(47, 35, 11, 0.98), rgba(8, 13, 25, 0.98));
  border: 1px solid rgba(250, 204, 21, 0.34);
}
.selected-card {
  min-height: 230px;
  background: rgba(2, 6, 23, 0.28);
  border-top: 1px solid rgba(250, 204, 21, 0.16);
}
</style>
