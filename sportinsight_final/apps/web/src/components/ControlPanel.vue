<template>
  <q-card class="glass-panel contrast-panel control-panel" flat>
    <q-card-section class="row items-center q-col-gutter-sm q-py-sm">

      <!-- Titre + chips statut -->
      <div class="col-12 col-lg-auto">
        <div class="row items-center q-gutter-sm no-wrap">
          <q-icon name="sports_soccer" color="cyan" size="22px" />
          <div>
            <div class="text-subtitle1 text-weight-bold match-title">{{ matchTitle }}</div>
            <div class="row q-gutter-xs q-mt-none">
              <q-chip dense square color="cyan-9" text-color="white" size="xs">Split test</q-chip>
              <q-chip dense square color="deep-purple-8" text-color="white" size="xs">Seuil {{ local.score_threshold.toFixed(2) }}</q-chip>
              <q-chip dense square color="amber-8" text-color="black" size="xs">{{ local.selected_classes.length }} classes</q-chip>
              <q-icon v-if="splitIntegrity?.is_disjoint" name="verified" color="positive" size="14px" class="self-center" />
            </div>
          </div>
        </div>
      </div>

      <!-- Sélecteur de match -->
      <div class="col-12 col-lg">
        <q-select
          v-model="selectedTestMatch"
          dark
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
          <template #prepend><q-icon name="search" /></template>
          <template #no-option>
            <q-item>
              <q-item-section class="text-blue-grey-2">
                Aucun match test — crée d'abord <code>splits/test.txt</code>.
              </q-item-section>
            </q-item>
          </template>
          <template #hint>{{ testMatches.length }} matchs disponibles</template>
        </q-select>
      </div>

      <!-- Boutons d'action -->
      <div class="col-12 col-lg-auto row q-gutter-xs items-center">
        <q-btn
          color="cyan" text-color="black" unelevated no-caps
          icon="play_arrow" label="Analyser"
          :loading="loading"
          @click="$emit('run', cloneRequest(local))"
        />
        <q-btn
          outline color="amber" no-caps
          icon="science" label="Démo"
          @click="$emit('load-demo')"
        />
        <q-btn
          flat color="cyan-2" round dense
          icon="tune"
          @click="advancedOpen = !advancedOpen"
        >
          <q-tooltip>Paramètres</q-tooltip>
        </q-btn>
      </div>
    </q-card-section>

    <!-- Paramètres avancés (collapsible) -->
    <q-slide-transition>
      <div v-show="advancedOpen">
        <q-separator dark />
        <q-card-section class="advanced-grid">
          <div class="row q-col-gutter-md">

            <!-- Colonne gauche : split info + checkpoint + import -->
            <div class="col-12 col-lg-7 q-gutter-sm">
              <div class="split-box q-pa-sm">
                <div class="row items-center justify-between q-mb-xs">
                  <div class="text-caption text-cyan-3 text-weight-bold">Protocole de split</div>
                  <q-btn dense flat color="cyan" icon="refresh" size="xs" no-caps @click="loadTestMatches" />
                </div>
                <div class="row q-gutter-xs">
                  <q-chip v-for="split in splits" :key="split.name" dense square size="xs"
                    :color="split.exists ? 'blue-grey-8' : 'red-10'" text-color="white">
                    {{ split.name }} · {{ split.count }}
                  </q-chip>
                </div>
                <div v-if="splitIntegrity && !splitIntegrity.is_disjoint" class="text-caption text-red-3 q-mt-xs">
                  Attention : chevauchement détecté entre les splits.
                </div>
              </div>

              <q-input v-model="local.checkpoint" dark dense outlined label="Checkpoint (.pt)" />

              <q-file v-model="predictionFile" dark dense outlined accept=".json,application/json"
                label="Importer predictions JSON" @update:model-value="handlePredictionFile">
                <template #prepend><q-icon name="upload_file" /></template>
              </q-file>
            </div>

            <!-- Colonne droite : contrôles d'analyse -->
            <div class="col-12 col-lg-5 q-gutter-sm">
              <q-btn-toggle
                v-model="local.half" spread no-caps rounded unelevated
                toggle-color="cyan" text-color="white" color="blue-grey-10"
                :options="[
                  { label: '1re mi-temps', value: 'first' },
                  { label: '2e mi-temps', value: 'second' },
                  { label: 'Match', value: 'both' }
                ]"
              />

              <div>
                <div class="row items-center justify-between">
                  <span class="text-caption">Seuil score</span>
                  <span class="mono text-caption">{{ local.score_threshold.toFixed(2) }}</span>
                </div>
                <q-slider v-model="local.score_threshold" color="cyan" :min="0.05" :max="0.95" :step="0.01" dense />
              </div>

              <div>
                <div class="row items-center justify-between">
                  <span class="text-caption">NMS temporelle</span>
                  <span class="mono text-caption">{{ local.nms_radius_sec.toFixed(1) }} s</span>
                </div>
                <q-slider v-model="local.nms_radius_sec" color="amber" :min="1" :max="20" :step="0.5" dense />
              </div>

              <q-option-group
                v-model="local.selected_classes" type="checkbox"
                :options="classOptions" color="cyan" dark dense
              />
            </div>
          </div>
        </q-card-section>
      </div>
    </q-slide-transition>
  </q-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Notify } from 'quasar'
import type { InferenceRequest, MatchSummary, SplitIntegrityResponse, SplitSummary } from '../types/predictions'
import { PRODUCT_CLASSES } from '../types/predictions'
import { getSplitIntegrity, getSplitMatches, getSplits } from '../services/api'

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
const splits = ref<SplitSummary[]>([])
const splitIntegrity = ref<SplitIntegrityResponse | null>(null)

const classOptions = PRODUCT_CLASSES.map((label) => ({ label, value: label }))

const matchTitle = computed(() => {
  const parts = local.match_dir.split(/[\\/]/).filter(Boolean)
  return parts.at(-1) ?? 'Match SoccerNet'
})

const emit = defineEmits<{
  run: [payload: InferenceRequest]
  'load-demo': []
  'load-json': [events: unknown[]]
}>()

onMounted(() => { void loadTestMatches() })

async function loadTestMatches() {
  matchesLoading.value = true
  try {
    const [splitRows, integrity, matches] = await Promise.all([
      getSplits('splits'),
      getSplitIntegrity('splits'),
      getSplitMatches('test', 'data/SoccerNet', 'splits', 500)
    ])
    splits.value = splitRows
    splitIntegrity.value = integrity
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
.match-title {
  max-width: 280px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.advanced-grid {
  background: rgba(2, 6, 23, 0.42);
  border-top: 1px solid rgba(56, 189, 248, 0.18);
}
.split-box {
  border: 1px solid rgba(34, 211, 238, 0.24);
  border-radius: 12px;
  background: rgba(8, 47, 73, 0.22);
}
</style>
