<template>
  <q-layout view="hHh lpR fFf">
    <q-header class="si-header">
      <q-toolbar class="q-px-lg">
        <q-toolbar-title>
          <span class="text-weight-bold">SportInsight</span>
          <span class="text-blue-8"> AI</span>
        </q-toolbar-title>
        <q-btn flat no-caps color="blue-8" icon="leaderboard" label="Performances" @click="perfOpen = true" />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-page class="q-pa-md">
        <PerformancePanel v-model="perfOpen" :run-id="runId" />

        <ControlPanel
          class="q-mb-sm"
          :initial-request="request"
          :loading="loading"
          @run="handleRun"
          @load-demo="handleLoadDemo"
          @load-json="handleLoadJson"
        />

        <div class="row q-col-gutter-md">
          <div class="col-12 col-lg-8">
            <TimelineView :events="events" :selected="selected" :summary="summary" @select="selected = $event" />
          </div>
          <div class="col-12 col-lg-4">
            <EventPanel :events="events" :selected="selected" :match-dir="request.match_dir" @select="selected = $event" />
          </div>
        </div>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Notify } from 'quasar'
import ControlPanel from '../components/ControlPanel.vue'
import EventPanel from '../components/EventPanel.vue'
import PerformancePanel from '../components/PerformancePanel.vue'
import TimelineView from '../components/TimelineView.vue'
import { loadDemoPredictions, runInference } from '../services/api'
import type { EventPrediction, InferenceRequest, RunSummary } from '../types/predictions'

const props = defineProps<{
  initialMatchDir?: string
  initialCheckpoint?: string
  initialScoreThreshold?: number
}>()

const DEFAULT_CLASSES = [
  'Penalty', 'Kick-off', 'Goal', 'Substitution',
  'Offside', 'Shots on target', 'Shots off target', 'Clearance',
  'Ball out of play', 'Throw-in', 'Foul', 'Indirect free-kick',
  'Direct free-kick', 'Corner', 'Yellow card', 'Red card', 'Yellow->red card',
]

const request = ref<InferenceRequest>({
  match_dir: 'data/SoccerNet/england_epl/2014-2015/2015-02-21 - 18-00 Chelsea 1 - 1 Burnley',
  checkpoint: 'runs/calf_17_slim_tdrop_sam/best.pt',
  half: 'both',
  score_threshold: 0.7,
  nms_radius_sec: 6.0,
  selected_classes: [...DEFAULT_CLASSES],
  device: 'auto'
})

const events = ref<EventPrediction[]>([])
const selected = ref<EventPrediction | null>(null)
const summary = ref<RunSummary | null>(null)
const loading = ref(false)
const perfOpen = ref(false)

const runId = computed(() => {
  const parts = request.value.checkpoint.replace(/\\/g, '/').split('/')
  return parts.length >= 2 ? parts[1] : parts[0]
})

// Props pour les matchs uploadés via VideoUploader
watch(() => props.initialMatchDir, (newVal) => {
  if (newVal) {
    request.value.match_dir = newVal
    triggerAutoAnalysis()
  }
}, { immediate: true })

watch(() => props.initialCheckpoint, (newVal) => {
  if (newVal) {
    request.value.checkpoint = newVal
  }
}, { immediate: true })

watch(() => props.initialScoreThreshold, (newVal) => {
  if (newVal !== undefined) {
    request.value.score_threshold = newVal
  }
}, { immediate: true })

async function triggerAutoAnalysis() {
  if (!props.initialMatchDir || !props.initialCheckpoint || loading.value) {
    return
  }
  await new Promise(resolve => setTimeout(resolve, 100))
  await handleRun(request.value)
}

function isEventPrediction(raw: unknown): raw is EventPrediction {
  const event = raw as Partial<EventPrediction>
  return typeof event.half === 'number'
    && typeof event.timestamp === 'number'
    && typeof event.gameTime === 'string'
    && typeof event.label === 'string'
    && typeof event.score === 'number'
}

function normalizeEvents(rawEvents: unknown[]): EventPrediction[] {
  return rawEvents
    .filter(isEventPrediction)
    .sort((a, b) => a.half - b.half || a.timestamp - b.timestamp)
}

function buildSummary(runId: string, source: string, loadedEvents: EventPrediction[]): RunSummary {
  const countsByClass: Record<string, number> = {}
  const countsByHalf: Record<string, number> = {}

  for (const event of loadedEvents) {
    countsByClass[event.label] = (countsByClass[event.label] ?? 0) + 1
    countsByHalf[String(event.half)] = (countsByHalf[String(event.half)] ?? 0) + 1
  }

  return {
    run_id: runId,
    match_dir: source,
    checkpoint: request.value.checkpoint,
    half: request.value.half,
    event_count: loadedEvents.length,
    counts_by_class: countsByClass,
    counts_by_half: countsByHalf
  }
}

function applyEvents(loadedEvents: EventPrediction[], runId: string, source: string) {
  events.value = loadedEvents
  selected.value = loadedEvents[0] ?? null
  summary.value = buildSummary(runId, source, loadedEvents)
}

async function handleRun(payload: InferenceRequest) {
  loading.value = true
  selected.value = null
  try {
    request.value = { ...payload, selected_classes: [...payload.selected_classes] }
    const response = await runInference(payload)
    events.value = response.events
    summary.value = response.summary
    selected.value = response.events[0] ?? null

    if (response.events.length === 0) {
      Notify.create({
        type: 'warning',
        message: 'Aucun événement détecté. Baisse le seuil score dans les paramètres avancés (0.30 puis 0.05 pour debug) ou vérifie que le match possède les features PCA512.'
      })
    } else {
      Notify.create({ type: 'positive', message: `${response.events.length} événements détectés` })
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Erreur inconnue'
    Notify.create({ type: 'negative', message })
  } finally {
    loading.value = false
  }
}

async function handleLoadDemo() {
  try {
    const demoEvents = await loadDemoPredictions()
    applyEvents(normalizeEvents(demoEvents), 'demo_clean_json', 'public/demo_predictions_clean.json')
    Notify.create({ type: 'positive', message: `${events.value.length} événements chargés depuis la démo JSON` })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Erreur inconnue'
    Notify.create({ type: 'negative', message })
  }
}

function handleLoadJson(rawEvents: unknown[]) {
  const parsedEvents = normalizeEvents(rawEvents)
  if (parsedEvents.length === 0) {
    Notify.create({ type: 'negative', message: 'Aucune prédiction valide dans le fichier JSON.' })
    return
  }
  applyEvents(parsedEvents, 'local_json', 'fichier JSON importé')
  Notify.create({ type: 'positive', message: `${parsedEvents.length} événements importés` })
}
</script>
