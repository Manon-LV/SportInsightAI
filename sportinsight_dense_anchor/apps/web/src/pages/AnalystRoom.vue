<template>
  <q-layout view="hHh lpR fFf">
    <q-header class="si-header">
      <q-toolbar class="q-px-lg">
        <q-toolbar-title>
          <span class="text-weight-bold">SportInsight</span>
          <span class="text-blue-2"> AI</span>
        </q-toolbar-title>
        <q-badge color="cyan" text-color="black">Alpha Jalon 3</q-badge>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-page class="q-pa-lg q-gutter-lg">
        <ControlPanel
          :initial-request="request"
          :loading="loading"
          @run="handleRun"
          @load-demo="handleLoadDemo"
          @load-json="handleLoadJson"
        />

        <ReportPanel :summary="summary" :events="events" />

        <div class="row q-col-gutter-lg">
          <div class="col-12 col-xl-8">
            <TimelineView :events="events" :selected="selected" @select="selected = $event" />
          </div>

          <div class="col-12 col-xl-4">
            <EventPanel :events="events" :selected="selected" :match-dir="request.match_dir" @select="selected = $event" />
          </div>
        </div>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Notify } from 'quasar'
import ControlPanel from '../components/ControlPanel.vue'
import EventPanel from '../components/EventPanel.vue'
import ReportPanel from '../components/ReportPanel.vue'
import TimelineView from '../components/TimelineView.vue'
import { loadDemoPredictions, runInference } from '../services/api'
import type { EventPrediction, InferenceRequest, RunSummary } from '../types/predictions'

const DEFAULT_CLASSES = ['Goal', 'Corner', 'Yellow card']

const request = ref<InferenceRequest>({
  match_dir: 'data/SoccerNet/england_epl/2014-2015/2015-02-21 - 18-00 Chelsea 1 - 1 Burnley',
  checkpoint: 'runs/dense_anchor/best.pt',
  half: 'both',
  score_threshold: 0.3,
  nms_radius_sec: 6.0,
  selected_classes: [...DEFAULT_CLASSES],
  device: 'auto'
})

const events = ref<EventPrediction[]>([])
const selected = ref<EventPrediction | null>(null)
const summary = ref<RunSummary | null>(null)
const loading = ref(false)

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
