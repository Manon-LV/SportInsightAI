<template>
  <q-card class="glass-panel contrast-panel control-panel" flat>
    <q-card-section class="row items-center no-wrap q-gutter-sm q-py-sm q-px-md">

      <q-icon name="sports_soccer" color="cyan-8" size="20px" class="col-auto" />

      <!-- Sélecteur de match -->
      <q-select
        class="col"
        v-model="selectedTestMatch"
        dense
        outlined
        emit-value
        map-options
        clearable
        use-input
        input-debounce="0"
        label="Match du split test"
        :options="filteredMatchOptions"
        :loading="matchesLoading"
        @filter="filterMatches"
        @update:model-value="handleSelectMatch"
      >
        <template #prepend><q-icon name="search" size="16px" /></template>
        <template #no-option>
          <q-item>
            <q-item-section class="text-blue-grey-6">
              Aucun match — crée d'abord <code>splits/test.txt</code>.
            </q-item-section>
          </q-item>
        </template>
      </q-select>

      <!-- Boutons d'action -->
      <div class="col-auto row q-gutter-xs no-wrap items-center">
        <q-btn
          color="cyan-8" text-color="white" unelevated no-caps
          icon="play_arrow" label="Analyser"
          :loading="loading"
          @click="$emit('run', cloneRequest(local))"
        />
        <q-btn
          flat color="blue-grey-7" no-caps
          icon="tune" label="Paramètres"
          @click="advancedOpen = true"
        />
        <q-btn
          flat color="blue-grey-7" no-caps
          icon="science" label="Démo"
          @click="$emit('load-demo')"
        />
      </div>
    </q-card-section>

    <!-- Dialog paramètres -->
    <q-dialog v-model="advancedOpen">
      <q-card class="params-dialog">
        <q-card-section class="row items-center justify-between q-pb-xs">
          <div class="text-subtitle1 text-weight-bold">Paramètres</div>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>

        <q-separator />

        <q-card-section class="q-gutter-md">
          <div class="row q-col-gutter-md">

            <!-- Colonne gauche : split info + checkpoint + import -->
            <div class="col-12 col-sm-7 q-gutter-sm">
<q-input v-model="local.checkpoint" dense outlined label="Checkpoint (.pt)" />

              <q-file v-model="predictionFile" dense outlined accept=".json,application/json"
                label="Importer predictions JSON" @update:model-value="handlePredictionFile">
                <template #prepend><q-icon name="upload_file" /></template>
              </q-file>
            </div>

            <!-- Colonne droite : contrôles d'analyse -->
            <div class="col-12 col-sm-5 q-gutter-sm">
              <q-btn-toggle
                v-model="local.half" spread no-caps rounded unelevated
                toggle-color="cyan-8" text-color="white" color="blue-grey-3"
                :options="[
                  { label: '1re mi-temps', value: 'first' },
                  { label: '2e mi-temps', value: 'second' },
                  { label: 'Match', value: 'both' }
                ]"
              />

              <div>
                <div class="row items-center justify-between q-mb-xs">
                  <span class="text-caption">Seuil score</span>
                  <input
                    v-model.number="local.score_threshold"
                    type="number" min="0.05" max="0.95" step="0.01"
                    class="slider-input"
                    @change="e => local.score_threshold = Math.min(0.95, Math.max(0.05, +(e.target as HTMLInputElement).value || 0.05))"
                  />
                </div>
                <q-slider v-model="local.score_threshold" color="cyan-8" :min="0.05" :max="0.95" :step="0.01" dense />
              </div>

              <div>
                <div class="row items-center justify-between q-mb-xs">
                  <span class="text-caption">NMS temporelle</span>
                  <input
                    v-model.number="local.nms_radius_sec"
                    type="number" min="1" max="20" step="0.5"
                    class="slider-input"
                    @change="e => local.nms_radius_sec = Math.min(20, Math.max(1, +(e.target as HTMLInputElement).value || 1))"
                  />
                </div>
                <q-slider v-model="local.nms_radius_sec" color="amber-8" :min="1" :max="20" :step="0.5" dense />
              </div>

              <q-select
                v-model="local.selected_classes"
                :options="classOptions"
                option-value="value"
                option-label="label"
                emit-value
                map-options
                multiple
                use-chips
                dense
                outlined
                label="Classes détectées"
                color="cyan-8"
              >
                <template #before-options>
                  <q-item dense clickable @click="toggleAllClasses">
                    <q-item-section>
                      <q-item-label class="text-caption text-cyan-8">
                        {{ local.selected_classes.length === classOptions.length ? 'Tout désélectionner' : 'Tout sélectionner' }}
                      </q-item-label>
                    </q-item-section>
                  </q-item>
                  <q-separator />
                </template>
              </q-select>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Notify } from 'quasar'
import type { InferenceRequest, MatchSummary } from '../types/predictions'
import { PRODUCT_CLASSES } from '../types/predictions'
import { getSplitMatches } from '../services/api'

const props = defineProps<{
  loading: boolean
  initialRequest: InferenceRequest
}>()

function cloneRequest(r: InferenceRequest): InferenceRequest {
  return { ...r, selected_classes: [...r.selected_classes] }
}

const local = reactive(cloneRequest(props.initialRequest))
const advancedOpen = ref(false)
const predictionFile = ref<File | null>(null)
const testMatches = ref<MatchSummary[]>([])
const matchOptions = ref<Array<{ label: string; value: string; caption: string }>>([])
const filteredMatchOptions = ref<Array<{ label: string; value: string; caption: string }>>([])
const matchesLoading = ref(false)
const selectedTestMatch = ref<string | null>(null)
const classOptions = PRODUCT_CLASSES.map((label) => ({ label, value: label }))

const emit = defineEmits<{
  run: [payload: InferenceRequest]
  'load-demo': []
  'load-json': [events: unknown[]]
}>()

onMounted(() => { void loadTestMatches() })

async function loadTestMatches() {
  matchesLoading.value = true
  try {
    const matches = await getSplitMatches('test', 'data/SoccerNet', 'splits', 500)
    testMatches.value = matches
    const usable = matches.filter((m) => m.has_first_half || m.has_second_half)
    matchOptions.value = usable.map((m) => ({
      label: `${m.name} · ${m.has_first_half ? 'H1' : ''}${m.has_first_half && m.has_second_half ? '+' : ''}${m.has_second_half ? 'H2' : ''}`,
      value: m.path,
      caption: m.id
    }))
    filteredMatchOptions.value = matchOptions.value
    if (!selectedTestMatch.value && matchOptions.value.length > 0) {
      selectedTestMatch.value = matchOptions.value[0].value
      local.match_dir = matchOptions.value[0].value
    }
  } catch (error) {
    Notify.create({ type: 'warning', message: error instanceof Error ? error.message : 'Impossible de charger les matchs test' })
  } finally {
    matchesLoading.value = false
  }
}

function toggleAllClasses() {
  if (local.selected_classes.length === classOptions.length) {
    local.selected_classes = []
  } else {
    local.selected_classes = classOptions.map((o) => o.value)
  }
}

function filterMatches(value: string, update: (cb: () => void) => void) {
  update(() => {
    const needle = value.toLowerCase().trim()
    filteredMatchOptions.value = needle
      ? matchOptions.value.filter((o) => `${o.label} ${o.caption}`.toLowerCase().includes(needle))
      : matchOptions.value
  })
}

function handleSelectMatch(value: string | null) {
  if (value) local.match_dir = value
}

async function handlePredictionFile(file: File | null) {
  if (!file) return
  try {
    const parsed = JSON.parse(await file.text())
    if (!Array.isArray(parsed)) throw new Error('Le fichier JSON doit contenir une liste de prédictions.')
    emit('load-json', parsed)
  } catch (error) {
    Notify.create({ type: 'negative', message: error instanceof Error ? error.message : 'JSON invalide' })
  }
}
</script>

<style scoped>
.params-dialog {
  width: 680px;
  max-width: 95vw;
}
.slider-input {
  width: 64px;
  border: none;
  border-bottom: 1px solid rgba(15, 23, 42, 0.25);
  background: transparent;
  text-align: right;
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: #0f172a;
  padding: 1px 2px;
  outline: none;
}
.slider-input:focus {
  border-bottom-color: #0891b2;
}
.slider-input::-webkit-inner-spin-button,
.slider-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.slider-input[type=number] {
  -moz-appearance: textfield;
}
</style>
