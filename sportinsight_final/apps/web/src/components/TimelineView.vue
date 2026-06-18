<template>
  <q-card class="glass-panel contrast-panel timeline-panel" flat>
    <q-card-section class="row items-center justify-between q-py-sm q-px-md">
      <div class="text-caption text-blue-8">
        {{ summary ? halfLabel : 'Timeline du match' }}
      </div>
    </q-card-section>

    <q-card-section>
      <svg class="timeline" viewBox="0 0 980 340" role="img" aria-label="Timeline des événements détectés">
        <defs>
          <linearGradient id="halfLine" x1="0" x2="1">
            <stop offset="0%" stop-color="#0284c7" stop-opacity="0.90" />
            <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.80" />
          </linearGradient>
        </defs>

        <g v-for="half in [1, 2]" :key="half" :transform="`translate(0 ${half === 1 ? 95 : 250})`">
          <text x="12" y="8" class="half-label">MT{{ half }}</text>
          <rect x="82" y="-80" width="858" height="110" rx="12" class="half-band" />
          <line x1="90" y1="0" x2="930" y2="0" class="axis" />
          <line v-for="tick in ticks" :key="tick" :x1="xForTime(tick)" :x2="xForTime(tick)" y1="-6" y2="6" class="tick" />
          <text v-for="tick in ticks" :key="`label-${tick}`" :x="xForTime(tick) - 12" y="24" class="tick-label">{{ tick / 60 }}'</text>

          <g v-for="event in byHalf(half)" :key="`${event.half}-${event.timestamp}-${event.label}`">
            <circle
              :cx="xForTime(event.timestamp)"
              :cy="-6 - laneForLabel(event.label) * 5"
              :r="radiusForScore(event.score)"
              :class="[
                'event-dot',
                event.label.replaceAll(' ', '-').toLowerCase(),
                isSelected(event) ? 'selected' : ''
              ]"
              @click="$emit('select', event)"
              @mouseenter="hoveredLabel = event.label"
              @mouseleave="hoveredLabel = null"
            >
              <title>{{ event.label }} · {{ event.gameTime }} · confiance {{ event.score.toFixed(2) }}</title>
            </circle>
          </g>
        </g>
      </svg>

      <div class="row q-gutter-xs q-mt-md legend">
        <q-chip
          v-for="cls in classes" :key="cls" dense square
          :class="[
            'legend-chip',
            `${cls.replaceAll(' ', '-').toLowerCase()}-dot`,
            hoveredLabel === cls ? 'legend-highlighted' : (hoveredLabel ? 'legend-dimmed' : '')
          ]"
        >
          {{ cls }}
        </q-chip>
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue' // computed gardé pour halfLabel
import { PRODUCT_CLASSES } from '../types/predictions'
import type { EventPrediction, RunSummary } from '../types/predictions'

const props = defineProps<{
  events: EventPrediction[]
  selected: EventPrediction | null
  summary: RunSummary | null
}>()

defineEmits<{
  select: [event: EventPrediction]
}>()


const halfLabel = computed(() => {
  if (!props.summary) return ''
  const match = props.summary.match_dir.split(/[\\/]/).at(-1) ?? ''
  const half =
    props.summary.half === 'both' ? 'Match complet' :
    props.summary.half === 'first' ? '1re mi-temps' : '2e mi-temps'
  return `${half} · ${match}`
})

const classes = PRODUCT_CLASSES
const hoveredLabel = ref<string | null>(null)

const maxHalfSeconds = 50 * 60
const ticks = [0, 15 * 60, 30 * 60, 45 * 60]

const lanes: Record<string, number> = {
  'Goal': 0,
  'Penalty': 1,
  'Shots on target': 2,
  'Shots off target': 3,
  'Corner': 4,
  'Direct free-kick': 5,
  'Indirect free-kick': 6,
  'Foul': 7,
  'Offside': 8,
  'Yellow card': 9,
  'Red card': 10,
  'Yellow->red card': 10,
  'Substitution': 11,
  'Kick-off': 12,
  'Clearance': 13,
  'Throw-in': 14,
  'Ball out of play': 15,
}

function byHalf(half: number): EventPrediction[] {
  return props.events.filter((event) => event.half === half)
}

function xForTime(seconds: number): number {
  return 90 + Math.min(seconds, maxHalfSeconds) / maxHalfSeconds * 840
}

function laneForLabel(label: string): number {
  return lanes[label] ?? 0
}

function radiusForScore(score: number): number {
  return 4 + score * 4
}

function isSelected(event: EventPrediction): boolean {
  if (!props.selected) return false
  return props.selected.half === event.half
    && props.selected.timestamp === event.timestamp
    && props.selected.label === event.label
}
</script>

<style scoped>
.timeline {
  width: 100%;
}
.half-band {
  fill: rgba(241, 245, 249, 0.65);
  stroke: rgba(15, 23, 42, 0.10);
}
.axis {
  stroke: url(#halfLine);
  stroke-width: 6;
  stroke-linecap: round;
  filter: drop-shadow(0 0 6px rgba(2, 132, 199, 0.32));
}
.tick {
  stroke: rgba(15, 23, 42, 0.32);
  stroke-width: 1.2;
}
.tick-label,
.half-label {
  fill: #1e293b;
  font-size: 12px;
}
.half-label {
  font-weight: 800;
}
.event-dot {
  cursor: pointer;
  stroke: rgba(255, 255, 255, 0.90);
  stroke-width: 2;
  fill: #0284c7;
  filter: drop-shadow(0 2px 4px rgba(15, 23, 42, 0.25));
  transition: transform 120ms ease, filter 120ms ease, stroke-width 120ms ease;
}
.event-dot:hover,
.event-dot.selected {
  stroke: #0f172a;
  stroke-width: 3.2;
  filter: drop-shadow(0 0 9px rgba(15, 23, 42, 0.40));
}
.goal               { fill: #16a34a; }
.corner             { fill: #0284c7; }
.yellow-card        { fill: #d97706; }
.red-card           { fill: #dc2626; }
.yellow--red-card   { fill: #dc2626; }
.penalty            { fill: #ea580c; }
.substitution       { fill: #9333ea; }
.offside            { fill: #0d9488; }
.foul               { fill: #ea580c; }
.shots-on-target    { fill: #0891b2; }
.shots-off-target   { fill: #64748b; }
.kick-off           { fill: #6366f1; }
.clearance          { fill: #14b8a6; }
.ball-out-of-play   { fill: #94a3b8; }
.throw-in           { fill: #06b6d4; }
.indirect-free-kick { fill: #f97316; }
.direct-free-kick   { fill: #f59e0b; }

.legend-chip {
  color: #1e293b;
  border: 1px solid rgba(15, 23, 42, 0.14);
  font-size: 11px;
  transition: transform 120ms ease, box-shadow 120ms ease, opacity 120ms ease;
}
.legend-highlighted {
  transform: scale(1.18);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.20);
  opacity: 1 !important;
  font-weight: 800;
  border-color: rgba(15, 23, 42, 0.30) !important;
}
.legend-dimmed {
  opacity: 0.30;
}
.goal-dot               { background: rgba(22,  163,  74, 0.18); color: #14532d; }
.corner-dot             { background: rgba(2,  132, 199, 0.18); color: #0c4a6e; }
.yellow-card-dot        { background: rgba(217, 119,   6, 0.18); color: #78350f; }
.red-card-dot           { background: rgba(220,  38,  38, 0.18); color: #7f1d1d; }
.penalty-dot            { background: rgba(234,  88,  12, 0.18); color: #7c2d12; }
.substitution-dot       { background: rgba(147,  51, 234, 0.18); color: #4c1d95; }
.offside-dot            { background: rgba(13,  148, 136, 0.18); color: #134e4a; }
.foul-dot               { background: rgba(234,  88,  12, 0.14); color: #7c2d12; }
.shots-on-target-dot    { background: rgba(8,  145, 178, 0.18); color: #083344; }
.shots-off-target-dot   { background: rgba(100, 116, 139, 0.18); color: #334155; }
.kick-off-dot           { background: rgba(99,  102, 241, 0.18); color: #312e81; }
.clearance-dot          { background: rgba(20,  184, 166, 0.18); color: #134e4a; }
.ball-out-of-play-dot   { background: rgba(100, 116, 139, 0.14); color: #334155; }
.throw-in-dot           { background: rgba(6,  182, 212, 0.18); color: #083344; }
.indirect-free-kick-dot { background: rgba(249, 115,  22, 0.18); color: #7c2d12; }
.direct-free-kick-dot   { background: rgba(245, 158,  11, 0.18); color: #78350f; }
.yellow-red-card-dot    { background: rgba(239,  68,  68, 0.14); color: #7f1d1d; }
</style>
