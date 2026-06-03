<template>
  <q-card class="glass-panel contrast-panel timeline-panel" flat>
    <q-card-section class="row items-center justify-between">
      <div>
        <div class="text-overline text-cyan-3">Timeline du match</div>
        <div class="text-h6">Actions détectées par mi-temps</div>
      </div>
      <q-chip color="cyan-8" text-color="black" square>{{ events.length }} événements</q-chip>
    </q-card-section>

    <q-card-section>
      <svg class="timeline" viewBox="0 0 980 350" role="img" aria-label="Timeline des événements détectés">
        <defs>
          <linearGradient id="halfLine" x1="0" x2="1">
            <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.95" />
            <stop offset="100%" stop-color="#facc15" stop-opacity="0.9" />
          </linearGradient>
        </defs>

        <g v-for="half in [1, 2]" :key="half" :transform="`translate(0 ${half === 1 ? 155 : 295})`">
          <text x="12" y="8" class="half-label">Mi-temps {{ half }}</text>
          <rect x="82" y="-140" width="858" height="170" rx="14" class="half-band" />
          <line x1="90" y1="0" x2="930" y2="0" class="axis" />
          <line v-for="tick in ticks" :key="tick" :x1="xForTime(tick)" :x2="xForTime(tick)" y1="-7" y2="7" class="tick" />
          <text v-for="tick in ticks" :key="`label-${tick}`" :x="xForTime(tick) - 14" y="25" class="tick-label">{{ tick / 60 }}'</text>

          <g v-for="event in byHalf(half)" :key="`${event.half}-${event.timestamp}-${event.label}`">
            <circle
              :cx="xForTime(event.timestamp)"
              :cy="-10 - laneForLabel(event.label) * 13"
              :r="radiusForScore(event.score)"
              :class="[
                'event-dot',
                event.label.replaceAll(' ', '-').toLowerCase(),
                isSelected(event) ? 'selected' : ''
              ]"
              @click="$emit('select', event)"
            >
              <title>{{ event.label }} · {{ event.gameTime }} · confiance {{ event.score.toFixed(2) }}</title>
            </circle>
          </g>
        </g>
      </svg>

      <div class="row q-gutter-xs q-mt-md legend">
        <q-chip v-for="cls in classes" :key="cls" dense square :class="`legend-chip ${cls.replaceAll(' ', '-').toLowerCase()}-dot`">
          {{ cls }}
        </q-chip>
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { PRODUCT_CLASSES } from '../types/predictions'
import type { EventPrediction } from '../types/predictions'

const props = defineProps<{
  events: EventPrediction[]
  selected: EventPrediction | null
}>()

defineEmits<{
  select: [event: EventPrediction]
}>()

const classes = PRODUCT_CLASSES

const maxHalfSeconds = 50 * 60
const ticks = [0, 15 * 60, 30 * 60, 45 * 60]

const lanes: Record<string, number> = {
  'Goal': 0,
  'Corner': 1,
  'Shots on target': 2,
  'Shots off target': 3,
  'Offside': 4,
  'Foul': 5,
  'Penalty': 6,
  'Substitution': 7,
  'Yellow card': 8,
  'Red card': 9,
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
  return 4 + score * 6
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
  min-height: 250px;
}
.half-band {
  fill: rgba(2, 6, 23, 0.46);
  stroke: rgba(226, 232, 240, 0.16);
}
.axis {
  stroke: url(#halfLine);
  stroke-width: 6;
  stroke-linecap: round;
  filter: drop-shadow(0 0 7px rgba(34, 211, 238, 0.42));
}
.tick {
  stroke: rgba(248, 250, 252, 0.58);
  stroke-width: 1.2;
}
.tick-label,
.half-label {
  fill: rgba(248, 250, 252, 0.94);
  font-size: 12px;
}
.half-label {
  font-weight: 800;
}
.event-dot {
  cursor: pointer;
  stroke: rgba(5, 7, 11, 0.88);
  stroke-width: 2;
  fill: #38bdf8;
  filter: drop-shadow(0 2px 5px rgba(0, 0, 0, 0.55));
  transition: transform 120ms ease, filter 120ms ease, stroke-width 120ms ease;
}
.event-dot:hover,
.event-dot.selected {
  stroke: #ffffff;
  stroke-width: 3.2;
  filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.62));
}
.goal               { fill: #22c55e; }
.corner             { fill: #38bdf8; }
.yellow-card        { fill: #facc15; }
.red-card           { fill: #ef4444; }
.penalty            { fill: #f97316; }
.substitution       { fill: #a78bfa; }
.offside            { fill: #2dd4bf; }
.foul               { fill: #fb923c; }
.shots-on-target    { fill: #67e8f9; }
.shots-off-target   { fill: #94a3b8; }

.legend-chip {
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.22);
  font-size: 11px;
}
.goal-dot               { background: rgba(34,  197,  94, 0.55); }
.corner-dot             { background: rgba(56,  189, 248, 0.55); }
.yellow-card-dot        { background: rgba(250, 204,  21, 0.72); color: #05070b; }
.red-card-dot           { background: rgba(239,  68,  68, 0.62); }
.penalty-dot            { background: rgba(249, 115,  22, 0.62); }
.substitution-dot       { background: rgba(167, 139, 250, 0.62); }
.offside-dot            { background: rgba(45,  212, 191, 0.62); color: #05070b; }
.foul-dot               { background: rgba(251, 146,  60, 0.62); }
.shots-on-target-dot    { background: rgba(103, 232, 249, 0.62); color: #05070b; }
.shots-off-target-dot   { background: rgba(148, 163, 184, 0.55); }
</style>
