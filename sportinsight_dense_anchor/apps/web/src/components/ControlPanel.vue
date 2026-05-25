<template>
  <q-card class="glass-panel contrast-panel control-panel" flat>
    <q-card-section class="row items-center q-col-gutter-md">
      <div class="col-12 col-xl-5">
        <div class="text-overline text-cyan-3">Analyse guidée</div>
        <div class="text-h5 text-weight-bold">{{ matchTitle }}</div>
        <div class="text-body2 text-blue-grey-1 q-mt-xs">
          Sélectionne un match du split test, lance l’analyse, puis lis la timeline et le résumé automatique.
        </div>
        <div class="row q-gutter-sm q-mt-sm">
          <q-chip dense square color="cyan-9" text-color="white">Split {{ activeSplit }}</q-chip>
          <q-chip dense square color="deep-purple-8" text-color="white">Seuil {{ local.score_threshold.toFixed(2) }}</q-chip>
          <q-chip dense square color="amber-8" text-color="black">{{ local.selected_classes.length }} classes visibles</q-chip>
        </div>
      </div>

      <div class="col-12 col-xl-4">
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
          <template #prepend>
            <q-icon name="sports_soccer" />
          </template>
          <template #no-option>
            <q-item>
              <q-item-section class="text-blue-grey-2">
                Aucun match test trouvé. Crée d’abord <code>splits/test.txt</code> avec le script de split.
              </q-item-section>
            </q-item>
          </template>
        </q-select>
        <div class="row items-center q-gutter-sm q-mt-xs text-caption text-blue-grey-2">
          <span>{{ testMatches.length }} matchs test disponibles</span>
          <q-icon v-if="splitIntegrity?.is_disjoint" name="verified" color="positive" size="16px" />
          <span v-if="splitIntegrity?.is_disjoint">splits disjoints</span>
          <span v-else-if="splitIntegrity" class="text-red-3">chevauchement détecté</span>
        </div>
      </div>

      <div class="col-12 col-xl-auto row q-gutter-sm justify-end">
        <q-btn
          color="cyan"
          text-color="black"
          unelevated
          size="lg"
          no-caps
          icon="play_arrow"
          label="Analyser le match"
          :loading="loading"
          @click="$emit('run', cloneRequest(local))"
        />
        <q-btn
          outline
          color="amber"
          size="lg"
          no-caps
          icon="science"
          label="Mode démo"
          @click="$emit('load-demo')"
        />
        <q-btn
          flat
          color="cyan-2"
          size="lg"
          no-caps
          icon="tune"
          label="Paramètres avancés"
          @click="advancedOpen = !advancedOpen"
        />
      </div>
    </q-card-section>

    <q-slide-transition>
      <div v-show="advancedOpen">
        <q-separator dark />
        <q-card-section class="advanced-grid q-col-gutter-md">
          <div class="row q-col-gutter-md">
            <div class="col-12 col-lg-7 q-gutter-md">
              <div class="split-box q-pa-md q-mb-md">
                <div class="row items-center justify-between q-mb-sm">
                  <div>
                    <div class="text-overline text-cyan-3">Protocole de split</div>
                    <div class="text-subtitle2">Inférence prioritaire sur <code>splits/test.txt</code></div>
                  </div>
                  <q-btn dense flat color="cyan" icon="refresh" label="Recharger" no-caps @click="loadTestMatches" />
                </div>
                <div class="row q-col-gutter-sm text-caption">
                  <div class="col-4" v-for="split in splits" :key="split.name">
                    <q-chip dense square :color="split.exists ? 'blue-grey-8' : 'red-10'" text-color="white">
                      {{ split.name }} · {{ split.count }}
                    </q-chip>
                  </div>
                </div>
                <q-banner v-if="splitIntegrity && !splitIntegrity.is_disjoint" rounded class="q-mt-sm bg-red-10 text-white">
                  Attention : au moins un match apparaît dans plusieurs splits. Regénère les splits avant l’évaluation.
                </q-banner>
              </div>

              <q-input v-model="local.match_dir" dark dense outlined label="Dossier match SoccerNet" />
              <q-input v-model="local.checkpoint" dark dense outlined label="Checkpoint modèle (.pt)" />

              <q-file
                v-model="predictionFile"
                dark
                dense
                outlined
                accept=".json,application/json"
                label="Importer predictions_clean.json"
                @update:model-value="handlePredictionFile"
              >
                <template #prepend>
                  <q-icon name="upload_file" />
                </template>
              </q-file>
            </div>

            <div class="col-12 col-lg-5 q-gutter-md">
              <q-btn-toggle
                v-model="local.half"
                spread
                no-caps
                rounded
                unelevated
                toggle-color="cyan"
                text-color="white"
                color="blue-grey-10"
                :options="[
                  { label: '1re mi-temps', value: 'first' },
                  { label: '2e mi-temps', value: 'second' },
                  { label: 'Match', value: 'both' }
                ]"
              />

              <div>
                <div class="row items-center justify-between q-mb-xs">
                  <span>Seuil score</span>
                  <span class="mono">{{ local.score_threshold.toFixed(2) }}</span>
                </div>
                <q-slider v-model="local.score_threshold" color="cyan" :min="0.05" :max="0.95" :step="0.01" />
              </div>

              <div>
                <div class="row items-center justify-between q-mb-xs">
                  <span>NMS temporelle</span>
                  <span class="mono">{{ local.nms_radius_sec.toFixed(1) }} s</span>
                </div>
                <q-slider v-model="local.nms_radius_sec" color="amber" :min="1" :max="20" :step="0.5" />
              </div>

              <q-option-group
                v-model="local.selected_classes"
                type="checkbox"
                :options="classOptions"
                color="cyan"
                dark
                dense
              />

              <q-chip dense square color="blue-grey-10" text-color="cyan-2">Features ResNet PCA512</q-chip>
            </div>
          </div>

          <q-separator dark class="q-my-lg" />

          <div class="download-box q-pa-md">
            <div class="row items-center justify-between q-col-gutter-md q-mb-md">
              <div class="col-12 col-lg">
                <div class="text-overline text-amber-3">Téléchargement SoccerNet</div>
                <div class="text-subtitle1 text-weight-bold">Ajouter les vidéos dans le dossier <code>data/SoccerNet</code></div>
                <div class="text-caption text-blue-grey-2 q-mt-xs">
                  Les vidéos nécessitent le mot de passe obtenu après signature du NDA SoccerNet. Pour la démo web, utilise 224p.
                </div>
              </div>
              <div class="col-12 col-lg-auto">
                <q-btn
                  color="amber"
                  text-color="black"
                  unelevated
                  no-caps
                  icon="download"
                  label="Télécharger vidéos"
                  :loading="downloadLoading"
                  @click="handleStartDownload"
                />
              </div>
            </div>

            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-4">
                <q-input v-model="download.root" dark dense outlined label="Dossier cible" />
              </div>
              <div class="col-12 col-md-4">
                <q-input
                  v-model="download.password"
                  dark
                  dense
                  outlined
                  type="password"
                  label="Mot de passe SoccerNet NDA"
                  hint="Optionnel si SOCCERNET_PASSWORD est défini"
                />
              </div>
              <div class="col-12 col-md-4">
                <q-select
                  v-model="download.resolution"
                  dark
                  dense
                  outlined
                  emit-value
                  map-options
                  label="Qualité vidéo"
                  :options="resolutionOptions"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-select
                  v-model="download.split"
                  dark
                  dense
                  outlined
                  multiple
                  emit-value
                  map-options
                  label="Splits"
                  :options="splitOptions"
                />
              </div>
              <div class="col-12 col-md-6">
                <q-input
                  v-model="download.game"
                  dark
                  dense
                  outlined
                  clearable
                  label="Match unique optionnel"
                  placeholder="england_epl/2014-2015/2015-02-21 - 18-00 Chelsea 1 - 1 Burnley"
                />
              </div>
              <div class="col-12">
                <q-toggle v-model="download.include_features" color="cyan" label="Télécharger aussi les features PCA512" />
                <q-toggle v-model="download.include_labels" color="cyan" label="Télécharger aussi Labels-v2.json" />
              </div>
            </div>

            <q-banner v-if="downloadStatus" rounded class="q-mt-md bg-blue-grey-10 text-blue-grey-1">
              <template #avatar>
                <q-spinner v-if="downloadStatus.status === 'running' || downloadStatus.status === 'queued'" color="amber" />
                <q-icon v-else-if="downloadStatus.status === 'done'" name="check_circle" color="positive" />
                <q-icon v-else name="error" color="negative" />
              </template>
              <div class="text-body2">
                <strong>{{ downloadStatus.status }}</strong> — {{ downloadStatus.message }}
              </div>
              <div class="text-caption text-blue-grey-3">
                Job {{ downloadStatus.job_id }} · fichiers : {{ downloadStatus.files.join(', ') }}
              </div>
              <div v-if="downloadStatus.error" class="text-caption text-red-3 q-mt-xs error-text">
                {{ downloadStatus.error.slice(0, 600) }}
              </div>
            </q-banner>
          </div>
        </q-card-section>
      </div>
    </q-slide-transition>
  </q-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Notify } from 'quasar'
import type { InferenceRequest, MatchSummary, SoccerNetDownloadStatus, SplitIntegrityResponse, SplitSummary } from '../types/predictions'
import { PRODUCT_CLASSES } from '../types/predictions'
import { getSoccerNetDownloadStatus, getSplitIntegrity, getSplitMatches, getSplits, startSoccerNetVideoDownload } from '../services/api'

const props = defineProps<{
  loading: boolean
  initialRequest: InferenceRequest
}>()

function cloneRequest(request: InferenceRequest): InferenceRequest {
  return { ...request, selected_classes: [...request.selected_classes] }
}

const local = reactive(cloneRequest(props.initialRequest))
const advancedOpen = ref(false)
const predictionFile = ref<File | null>(null)
const downloadLoading = ref(false)
const downloadStatus = ref<SoccerNetDownloadStatus | null>(null)
const testMatches = ref<MatchSummary[]>([])
const matchOptions = ref<Array<{ label: string; value: string; caption: string }>>([])
const filteredMatchOptions = ref<Array<{ label: string; value: string; caption: string }>>([])
const matchesLoading = ref(false)
const selectedTestMatch = ref<string | null>(null)
const splits = ref<SplitSummary[]>([])
const splitIntegrity = ref<SplitIntegrityResponse | null>(null)
const activeSplit = 'test'

const download = reactive({
  root: 'data/SoccerNet',
  password: '',
  split: ['train', 'valid', 'test'] as Array<'train' | 'valid' | 'test' | 'challenge'>,
  resolution: '224p' as '224p' | '720p' | 'both',
  game: '',
  include_features: false,
  include_labels: false
})

const splitOptions = [
  { label: 'train', value: 'train' },
  { label: 'valid', value: 'valid' },
  { label: 'test', value: 'test' },
  { label: 'challenge', value: 'challenge' }
]

const resolutionOptions = [
  { label: '224p — recommandé démo', value: '224p' },
  { label: '720p — plus lourd', value: '720p' },
  { label: '224p + 720p', value: 'both' }
]

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

onMounted(() => {
  void loadTestMatches()
})

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
    const usableMatches = matches.filter((match) => match.has_first_half || match.has_second_half)
    matchOptions.value = usableMatches.map((match) => ({
      label: `${match.name} · ${match.has_first_half ? 'H1' : ''}${match.has_first_half && match.has_second_half ? '+' : ''}${match.has_second_half ? 'H2' : ''}`,
      value: match.path,
      caption: match.id
    }))
    filteredMatchOptions.value = matchOptions.value
    if (matches.length > 0 && usableMatches.length === 0) {
      Notify.create({
        type: 'warning',
        message: 'Les matchs du split test existent, mais aucun ne possède de features PCA512 détectables. Télécharge ou copie 1_ResNET_PCA512.npy et 2_ResNET_PCA512.npy.'
      })
    }
    if (!selectedTestMatch.value && matchOptions.value.length > 0) {
      selectedTestMatch.value = matchOptions.value[0].value
      local.match_dir = matchOptions.value[0].value
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Impossible de charger les matchs test'
    Notify.create({ type: 'warning', message })
  } finally {
    matchesLoading.value = false
  }
}

function filterMatches(value: string, update: (callback: () => void) => void) {
  update(() => {
    const needle = value.toLowerCase().trim()
    filteredMatchOptions.value = needle
      ? matchOptions.value.filter((option) => `${option.label} ${option.caption}`.toLowerCase().includes(needle))
      : matchOptions.value
  })
}

function handleSelectMatch(value: string | null) {
  if (value) {
    local.match_dir = value
  }
}

async function handlePredictionFile(file: File | null) {
  if (!file) return
  try {
    const text = await file.text()
    const parsed = JSON.parse(text)
    if (!Array.isArray(parsed)) {
      throw new Error('Le fichier JSON doit contenir une liste de prédictions.')
    }
    emit('load-json', parsed)
  } catch (error) {
    const message = error instanceof Error ? error.message : 'JSON invalide'
    Notify.create({ type: 'negative', message })
  }
}

async function handleStartDownload() {
  downloadLoading.value = true
  try {
    const status = await startSoccerNetVideoDownload({
      root: download.root,
      password: download.password.trim() ? download.password.trim() : null,
      split: download.split,
      resolution: download.resolution,
      game: download.game.trim() ? download.game.trim() : null,
      include_features: download.include_features,
      include_labels: download.include_labels
    })
    downloadStatus.value = status
    Notify.create({ type: 'positive', message: `Téléchargement lancé : ${status.job_id}` })
    pollDownload(status.job_id)
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Impossible de lancer le téléchargement'
    Notify.create({ type: 'negative', message })
  } finally {
    downloadLoading.value = false
  }
}

function pollDownload(jobId: string) {
  const timer = window.setInterval(async () => {
    try {
      const status = await getSoccerNetDownloadStatus(jobId)
      downloadStatus.value = status
      if (status.status === 'done' || status.status === 'error') {
        window.clearInterval(timer)
      }
    } catch {
      window.clearInterval(timer)
    }
  }, 2500)
}
</script>

<style scoped>
.advanced-grid {
  background: rgba(2, 6, 23, 0.42);
  border-top: 1px solid rgba(56, 189, 248, 0.18);
}

.download-box {
  border: 1px solid rgba(250, 204, 21, 0.22);
  border-radius: 16px;
  background: rgba(113, 63, 18, 0.16);
}

.split-box {
  border: 1px solid rgba(34, 211, 238, 0.24);
  border-radius: 16px;
  background: rgba(8, 47, 73, 0.22);
}

.error-text {
  white-space: pre-wrap;
  max-height: 120px;
  overflow: auto;
}
</style>
