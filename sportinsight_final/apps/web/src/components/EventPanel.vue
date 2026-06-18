<template>
  <q-card class="glass-panel contrast-panel event-panel" flat>
    <q-card-section class="row items-center justify-between q-py-sm q-px-md">
      <div>
        <div class="text-overline text-amber-9">Événement sélectionné</div>
        <div v-if="selected" class="row items-center q-gutter-xs q-mt-none">
          <q-chip dense square :color="colorFor(selected.label)" text-color="white" size="sm">
            {{ selected.label }}
          </q-chip>
          <span class="text-caption text-blue-grey-6">{{ selected.gameTime }}</span>
          <q-badge outline color="blue-grey-5" class="q-ml-xs">{{ selected.score.toFixed(2) }}</q-badge>
        </div>
        <div v-else class="text-caption text-blue-grey-6">Sélectionne un point sur la timeline</div>
      </div>
      <q-btn flat dense no-caps icon="list" color="amber-8" label="Toutes les actions" @click="dialogOpen = true" />
    </q-card-section>

    <q-separator />

    <q-card-section v-if="selected" class="q-py-sm">
      <VideoClipPreview :event="selected" :match-dir="matchDir" />
    </q-card-section>

    <q-dialog v-model="dialogOpen">
      <q-card class="event-dialog">
        <q-card-section class="row items-center justify-between q-py-sm">
          <div>
            <div class="text-overline text-amber-9">Liste complète</div>
            <div class="text-h6">{{ events.length }} actions détectées</div>
          </div>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>

        <q-separator />

        <q-list separator style="max-height: 70vh; overflow: auto">
          <q-item
            v-for="event in events"
            :key="`${event.half}-${event.timestamp}-${event.label}`"
            clickable dense
            v-close-popup
            @click="$emit('select', event)"
          >
            <q-item-section avatar>
              <q-avatar :color="colorFor(event.label)" text-color="white" size="28px" font-size="11px">
                {{ event.label.slice(0, 1) }}
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ event.label }}</q-item-label>
              <q-item-label caption>{{ event.gameTime }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge color="blue-grey-5">{{ event.score.toFixed(2) }}</q-badge>
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
  'Goal':                'green-7',
  'Penalty':             'orange-8',
  'Shots on target':     'cyan-7',
  'Shots off target':    'blue-grey-6',
  'Corner':              'light-blue-7',
  'Direct free-kick':    'amber-7',
  'Indirect free-kick':  'orange-6',
  'Foul':                'deep-orange-7',
  'Offside':             'teal-6',
  'Yellow card':         'amber-8',
  'Red card':            'red-7',
  'Yellow->red card':    'red-8',
  'Substitution':        'purple-7',
  'Kick-off':            'indigo-6',
  'Clearance':           'teal-7',
  'Throw-in':            'cyan-6',
  'Ball out of play':    'blue-grey-5',
}

function colorFor(label: string): string {
  return CLASS_COLORS[label] ?? 'blue-grey-7'
}
</script>

<style scoped>
.event-dialog {
  width: 580px;
  max-width: 92vw;
  background: linear-gradient(135deg, rgba(254, 243, 199, 0.60), rgba(255, 255, 255, 0.98));
  border: 1px solid rgba(217, 119, 6, 0.24);
}
</style>
