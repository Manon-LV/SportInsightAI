<template>
  <q-card class="si-card upload-card">
    <q-card-section class="si-header-section">
      <div class="text-h6 text-weight-bold">📤 Importer des Match</div>
      <div class="text-caption text-grey-7">Choisissez comment importer votre match</div>
    </q-card-section>

    <q-separator />

    <!-- Mode de sélection -->
    <q-card-section class="q-pt-lg">
      <div class="q-mb-lg">
        <div class="text-subtitle2 text-weight-bold q-mb-md">Mode d'import</div>
        <q-option-group
          v-model="importMode"
          :options="[
            { label: '📹 Uploader des vidéos (extraction auto)', value: 'video' },
            { label: '📊 Importer des features pré-extraites (.npy)', value: 'features' }
          ]"
          color="cyan"
          inline
          class="q-mb-md"
        />
      </div>
    </q-card-section>

    <q-separator />

    <!-- MODE VIDÉO -->
    <q-card-section v-if="importMode === 'video'" class="q-pt-lg">
      <!-- Étape 1: Nom du match -->
      <div class="q-mb-lg">
        <div class="text-subtitle2 text-weight-bold q-mb-md">
          1️⃣ Informations du match
        </div>
        <q-input
          v-model="matchName"
          label="Nom du match (ex: PSG vs Lyon)"
          outlined
          dense
          :disable="uploading"
          class="q-mb-md"
        />
      </div>

      <!-- Étape 2: Upload des vidéos -->
      <div class="q-mb-lg">
        <div class="text-subtitle2 text-weight-bold q-mb-md">
          2️⃣ Upload des vidéos
        </div>

        <!-- Mi-temps 1 -->
        <div class="q-mb-md">
          <div class="text-body2 q-mb-sm">Mi-temps 1</div>
          <div
            class="upload-zone"
            :class="{ 'upload-zone-hover': dragOverHalf1, 'upload-zone-success': videoFile1 }"
            @dragover.prevent="dragOverHalf1 = true"
            @dragleave.prevent="dragOverHalf1 = false"
            @drop.prevent="handleDropHalf1"
          >
            <div v-if="!videoFile1" class="text-center q-py-lg">
              <q-icon name="cloud_upload" size="3em" class="text-grey-6 q-mb-md" />
              <div class="text-body2">Glissez-déposez la vidéo</div>
              <div class="text-caption text-grey-7">ou</div>
              <q-btn
                flat
                size="sm"
                label="Sélectionner"
                @click="selectFileHalf1"
                :disable="uploading"
              />
            </div>
            <div v-else class="text-center q-py-md">
              <q-icon name="check_circle" size="2em" class="text-positive q-mb-sm" />
              <div class="text-body2 text-weight-bold">{{ videoFile1.name }}</div>
              <div class="text-caption text-grey-7">{{ formatFileSize(videoFile1.size) }}</div>
              <q-btn
                flat
                size="sm"
                label="Changer"
                @click="selectFileHalf1"
                :disable="uploading"
                class="q-mt-sm"
              />
            </div>
          </div>
          <input
            ref="inputHalf1"
            type="file"
            accept="video/*"
            style="display: none"
            @change="handleFileSelectHalf1"
          />
        </div>

        <!-- Mi-temps 2 -->
        <div class="q-mb-md">
          <div class="text-body2 q-mb-sm">Mi-temps 2</div>
          <div
            class="upload-zone"
            :class="{ 'upload-zone-hover': dragOverHalf2, 'upload-zone-success': videoFile2 }"
            @dragover.prevent="dragOverHalf2 = true"
            @dragleave.prevent="dragOverHalf2 = false"
            @drop.prevent="handleDropHalf2"
          >
            <div v-if="!videoFile2" class="text-center q-py-lg">
              <q-icon name="cloud_upload" size="3em" class="text-grey-6 q-mb-md" />
              <div class="text-body2">Glissez-déposez la vidéo</div>
              <div class="text-caption text-grey-7">ou</div>
              <q-btn
                flat
                size="sm"
                label="Sélectionner"
                @click="selectFileHalf2"
                :disable="uploading"
              />
            </div>
            <div v-else class="text-center q-py-md">
              <q-icon name="check_circle" size="2em" class="text-positive q-mb-sm" />
              <div class="text-body2 text-weight-bold">{{ videoFile2.name }}</div>
              <div class="text-caption text-grey-7">{{ formatFileSize(videoFile2.size) }}</div>
              <q-btn
                flat
                size="sm"
                label="Changer"
                @click="selectFileHalf2"
                :disable="uploading"
                class="q-mt-sm"
              />
            </div>
          </div>
          <input
            ref="inputHalf2"
            type="file"
            accept="video/*"
            style="display: none"
            @change="handleFileSelectHalf2"
          />
        </div>
      </div>

      <!-- Progression -->
      <div v-if="uploading" class="q-mb-lg">
        <div class="text-subtitle2 text-weight-bold q-mb-md">
          3️⃣ Progression: {{ uploadStep }}
        </div>
        <q-linear-progress
          :value="uploadProgress"
          color="cyan"
          class="q-mb-md"
        />
        <div class="text-caption text-grey-7">
          {{ uploadMessage }}
        </div>
      </div>

      <!-- Sélection du checkpoint -->
      <div v-if="!uploading" class="q-mb-lg">
        <div class="text-subtitle2 text-weight-bold q-mb-md">
          3️⃣ Modèle d'analyse
        </div>
        <q-select
          v-model="selectedCheckpoint"
          :options="checkpointOptions"
          label="Checkpoint"
          outlined
          dense
          emit-value
          map-options
          @update:model-value="selectedCheckpoint = $event"
        />
        <div class="text-caption text-grey-7 q-mt-sm">
          Les features seront extraites automatiquement après l'upload
        </div>
      </div>

      <!-- Seuil de confiance -->
      <div v-if="!uploading" class="q-mb-lg">
        <div class="text-subtitle2 text-weight-bold q-mb-md">
          4️⃣ Seuil de confiance
        </div>
        <div class="row items-center q-gutter-md">
          <q-slider
            v-model="scoreThreshold"
            :min="0"
            :max="1"
            :step="0.05"
            label
            label-always
            :label-value="`${(scoreThreshold * 100).toFixed(0)}%`"
            color="cyan"
            class="q-flex-grow-1"
          />
        </div>
        <div class="text-caption text-grey-7 q-mt-sm">
          Plus bas = plus d'événements détectés (mais plus de faux positifs)
        </div>
      </div>

      <!-- Boutons d'action -->
      <div class="row q-gutter-md q-mt-lg">
        <q-btn
          flat
          label="Annuler"
          @click="reset"
          :disable="uploading"
        />
        <q-btn
          unelevated
          label="Uploader et analyser"
          color="cyan"
          text-color="black"
          icon-right="cloud_upload"
          @click="handleUpload"
          :disable="!canUpload || uploading"
          :loading="uploading"
          class="q-flex-grow-1"
        />
      </div>
    </q-card-section>

    <!-- MODE FEATURES -->
    <q-card-section v-if="importMode === 'features'" class="q-pt-lg">
      <!-- Étape 1: Nom du match -->
      <div class="q-mb-lg">
        <div class="text-subtitle2 text-weight-bold q-mb-md">
          1️⃣ Informations du match
        </div>
        <q-input
          v-model="matchName"
          label="Nom du match (ex: PSG vs Lyon)"
          outlined
          dense
          :disable="uploading"
          class="q-mb-md"
        />
      </div>

      <!-- Étape 2: Upload des fichiers .npy -->
      <div class="q-mb-lg">
        <div class="text-subtitle2 text-weight-bold q-mb-md">
          2️⃣ Upload des fichiers de features (.npy)
        </div>

        <!-- Features Mi-temps 1 -->
        <div class="q-mb-md">
          <div class="text-body2 q-mb-sm">Features Mi-temps 1 (1_ResNET_TF2_PCA512.npy)</div>
          <div
            class="upload-zone"
            :class="{ 'upload-zone-hover': dragOverFeatures1, 'upload-zone-success': featuresFile1 }"
            @dragover.prevent="dragOverFeatures1 = true"
            @dragleave.prevent="dragOverFeatures1 = false"
            @drop.prevent="handleDropFeatures1"
          >
            <div v-if="!featuresFile1" class="text-center q-py-lg">
              <q-icon name="data_usage" size="3em" class="text-grey-6 q-mb-md" />
              <div class="text-body2">Glissez-déposez le fichier .npy</div>
              <div class="text-caption text-grey-7">ou</div>
              <q-btn
                flat
                size="sm"
                label="Sélectionner"
                @click="selectFileFeatures1"
                :disable="uploading"
              />
            </div>
            <div v-else class="text-center q-py-md">
              <q-icon name="check_circle" size="2em" class="text-positive q-mb-sm" />
              <div class="text-body2 text-weight-bold">{{ featuresFile1.name }}</div>
              <div class="text-caption text-grey-7">{{ formatFileSize(featuresFile1.size) }}</div>
              <q-btn
                flat
                size="sm"
                label="Changer"
                @click="selectFileFeatures1"
                :disable="uploading"
                class="q-mt-sm"
              />
            </div>
          </div>
          <input
            ref="inputFeatures1"
            type="file"
            accept=".npy"
            style="display: none"
            @change="handleFileSelectFeatures1"
          />
        </div>

        <!-- Features Mi-temps 2 -->
        <div class="q-mb-md">
          <div class="text-body2 q-mb-sm">Features Mi-temps 2 (2_ResNET_TF2_PCA512.npy)</div>
          <div
            class="upload-zone"
            :class="{ 'upload-zone-hover': dragOverFeatures2, 'upload-zone-success': featuresFile2 }"
            @dragover.prevent="dragOverFeatures2 = true"
            @dragleave.prevent="dragOverFeatures2 = false"
            @drop.prevent="handleDropFeatures2"
          >
            <div v-if="!featuresFile2" class="text-center q-py-lg">
              <q-icon name="data_usage" size="3em" class="text-grey-6 q-mb-md" />
              <div class="text-body2">Glissez-déposez le fichier .npy</div>
              <div class="text-caption text-grey-7">ou</div>
              <q-btn
                flat
                size="sm"
                label="Sélectionner"
                @click="selectFileFeatures2"
                :disable="uploading"
              />
            </div>
            <div v-else class="text-center q-py-md">
              <q-icon name="check_circle" size="2em" class="text-positive q-mb-sm" />
              <div class="text-body2 text-weight-bold">{{ featuresFile2.name }}</div>
              <div class="text-caption text-grey-7">{{ formatFileSize(featuresFile2.size) }}</div>
              <q-btn
                flat
                size="sm"
                label="Changer"
                @click="selectFileFeatures2"
                :disable="uploading"
                class="q-mt-sm"
              />
            </div>
          </div>
          <input
            ref="inputFeatures2"
            type="file"
            accept=".npy"
            style="display: none"
            @change="handleFileSelectFeatures2"
          />
        </div>
      </div>

      <!-- Étape 2b: Upload vidéos optionnelles -->
      <div class="q-mb-lg">
        <div class="text-subtitle2 text-weight-bold q-mb-md">
          2b. Vidéos du match (optionnel — pour la lecture dans l'interface)
        </div>
        <div class="text-caption text-grey-7 q-mb-md">
          Ajoutez les vidéos .mkv/.mp4 pour visualiser les extraits dans l'AnalystRoom
        </div>

        <!-- Vidéo Mi-temps 1 -->
        <div class="q-mb-md">
          <div class="text-body2 q-mb-sm">Vidéo Mi-temps 1 (.mkv / .mp4)</div>
          <div
            class="upload-zone"
            :class="{ 'upload-zone-hover': dragOverVideo1, 'upload-zone-success': videoOptFile1 }"
            @dragover.prevent="dragOverVideo1 = true"
            @dragleave.prevent="dragOverVideo1 = false"
            @drop.prevent="handleDropVideo1"
          >
            <div v-if="!videoOptFile1" class="text-center q-py-md">
              <q-icon name="movie" size="2em" class="text-grey-5 q-mb-sm" />
              <div class="text-body2 text-grey-6">Glissez-déposez la vidéo</div>
              <q-btn flat size="sm" label="Sélectionner" @click="selectVideoOpt1" :disable="uploading" class="q-mt-sm" />
            </div>
            <div v-else class="text-center q-py-sm">
              <q-icon name="check_circle" size="1.5em" class="text-positive q-mb-xs" />
              <div class="text-body2 text-weight-bold">{{ videoOptFile1.name }}</div>
              <div class="text-caption text-grey-7">{{ formatFileSize(videoOptFile1.size) }}</div>
              <q-btn flat size="sm" label="Changer" @click="selectVideoOpt1" :disable="uploading" />
            </div>
          </div>
          <input ref="inputVideoOpt1" type="file" accept="video/*" style="display:none" @change="handleFileVideoOpt1" />
        </div>

        <!-- Vidéo Mi-temps 2 -->
        <div class="q-mb-md">
          <div class="text-body2 q-mb-sm">Vidéo Mi-temps 2 (.mkv / .mp4)</div>
          <div
            class="upload-zone"
            :class="{ 'upload-zone-hover': dragOverVideo2, 'upload-zone-success': videoOptFile2 }"
            @dragover.prevent="dragOverVideo2 = true"
            @dragleave.prevent="dragOverVideo2 = false"
            @drop.prevent="handleDropVideo2"
          >
            <div v-if="!videoOptFile2" class="text-center q-py-md">
              <q-icon name="movie" size="2em" class="text-grey-5 q-mb-sm" />
              <div class="text-body2 text-grey-6">Glissez-déposez la vidéo</div>
              <q-btn flat size="sm" label="Sélectionner" @click="selectVideoOpt2" :disable="uploading" class="q-mt-sm" />
            </div>
            <div v-else class="text-center q-py-sm">
              <q-icon name="check_circle" size="1.5em" class="text-positive q-mb-xs" />
              <div class="text-body2 text-weight-bold">{{ videoOptFile2.name }}</div>
              <div class="text-caption text-grey-7">{{ formatFileSize(videoOptFile2.size) }}</div>
              <q-btn flat size="sm" label="Changer" @click="selectVideoOpt2" :disable="uploading" />
            </div>
          </div>
          <input ref="inputVideoOpt2" type="file" accept="video/*" style="display:none" @change="handleFileVideoOpt2" />
        </div>
      </div>

      <!-- Sélection du checkpoint -->
      <div class="q-mb-lg">
        <div class="text-subtitle2 text-weight-bold q-mb-md">
          3️⃣ Modèle d'analyse
        </div>
        <q-select
          v-model="selectedCheckpoint"
          :options="checkpointOptions"
          label="Checkpoint"
          outlined
          dense
          emit-value
          map-options
          @update:model-value="selectedCheckpoint = $event"
        />
        <div class="text-caption text-grey-7 q-mt-sm">
          Les features seront importées et prêtes pour l'analyse
        </div>
      </div>

      <!-- Seuil de confiance -->
      <div class="q-mb-lg">
        <div class="text-subtitle2 text-weight-bold q-mb-md">
          4️⃣ Seuil de confiance
        </div>
        <div class="row items-center q-gutter-md">
          <q-slider
            v-model="scoreThreshold"
            :min="0"
            :max="1"
            :step="0.05"
            label
            label-always
            :label-value="`${(scoreThreshold * 100).toFixed(0)}%`"
            color="cyan"
            class="q-flex-grow-1"
          />
        </div>
        <div class="text-caption text-grey-7 q-mt-sm">
          Plus bas = plus d'événements détectés (mais plus de faux positifs)
        </div>
      </div>

      <!-- Boutons d'action -->
      <div class="row q-gutter-md q-mt-lg">
        <q-btn
          flat
          label="Annuler"
          @click="reset"
          :disable="uploading"
        />
        <q-btn
          unelevated
          label="Importer et analyser"
          color="cyan"
          text-color="black"
          icon-right="data_usage"
          @click="handleFeaturesImport"
          :disable="!canImportFeatures || uploading"
          :loading="uploading"
          class="q-flex-grow-1"
        />
      </div>
    </q-card-section>
    <q-separator v-if="jobId" />
    <q-card-section v-if="jobId" class="bg-blue-1">
      <div class="text-subtitle2 text-weight-bold q-mb-md">
        ✅ Upload en cours
      </div>
      <div class="q-gutter-md">
        <div class="row items-center">
          <div class="text-body2">Job ID:</div>
          <div class="text-body2 text-weight-bold q-ml-md mono">{{ jobId }}</div>
          <q-btn flat dense icon="content_copy" size="sm" @click="copyJobId" />
        </div>
        <div class="row items-center">
          <div class="text-body2">Status:</div>
          <div class="q-ml-md">
            <q-badge :color="statusColor" :label="jobStatus" />
          </div>
        </div>
        <div class="row items-center">
          <div class="text-body2">Match directory:</div>
          <div class="text-body2 text-weight-bold q-ml-md mono text-caption">{{ matchDir }}</div>
        </div>
      </div>

      <!-- Actions après upload -->
      <div class="row q-gutter-md q-mt-lg">
        <q-btn
          outline
          label="Rafraîchir"
          icon="refresh"
          @click="refreshJobStatus"
          :disable="uploading"
        />
        <q-btn
          outline
          label="Analyser maintenant"
          icon="play_arrow"
          @click="handleAnalyze"
          :disable="jobStatus !== 'processing' && jobStatus !== 'done'"
        />
        <q-btn
          flat
          label="Nouveau upload"
          @click="reset"
          :disable="uploading"
        />
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Notify } from 'quasar'
import {
  createUploadJob,
  uploadVideo,
  finalizeUpload,
  extractFeatures,
  getUploadStatus,
  listCheckpoints,
  uploadFeaturesFile
} from '../services/api'

// État du formulaire
const matchName = ref('')
const videoFile1 = ref<File | null>(null)
const videoFile2 = ref<File | null>(null)
const selectedCheckpoint = ref<string>('')
const importMode = ref<'video' | 'features'>('video')
const scoreThreshold = ref(0.3) // Nouveau: seuil de confiance

// État des fichiers de features
const featuresFile1 = ref<File | null>(null)
const featuresFile2 = ref<File | null>(null)

// Vidéos optionnelles (mode features)
const videoOptFile1 = ref<File | null>(null)
const videoOptFile2 = ref<File | null>(null)
const dragOverVideo1 = ref(false)
const dragOverVideo2 = ref(false)

// État de l'upload
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStep = ref('Initialisation...')
const uploadMessage = ref('')
const jobId = ref('')
const jobStatus = ref<string>('')
const matchDir = ref('')

// Drag and drop
const dragOverHalf1 = ref(false)
const dragOverHalf2 = ref(false)
const dragOverFeatures1 = ref(false)
const dragOverFeatures2 = ref(false)

// Références
const inputHalf1 = ref<HTMLInputElement>()
const inputHalf2 = ref<HTMLInputElement>()
const inputFeatures1 = ref<HTMLInputElement>()
const inputFeatures2 = ref<HTMLInputElement>()
const inputVideoOpt1 = ref<HTMLInputElement>()
const inputVideoOpt2 = ref<HTMLInputElement>()

// Options
const checkpointOptions = ref<Array<{ label: string; value: string }>>([])

// Computed
const canUpload = computed(() => {
  return matchName.value.trim() && videoFile1.value && videoFile2.value && selectedCheckpoint.value && !uploading.value
})

const canImportFeatures = computed(() => {
  return matchName.value.trim() && featuresFile1.value && featuresFile2.value && selectedCheckpoint.value && !uploading.value
})

const statusColor = computed(() => {
  switch (jobStatus.value) {
    case 'uploading': return 'blue'
    case 'processing': return 'orange'
    case 'done': return 'positive'
    case 'error': return 'negative'
    default: return 'grey'
  }
})

// Méthodes
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function selectFileHalf1() {
  inputHalf1.value?.click()
}

function selectFileHalf2() {
  inputHalf2.value?.click()
}

function handleFileSelectHalf1(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.[0]) {
    videoFile1.value = input.files[0]
  }
}

function handleFileSelectHalf2(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.[0]) {
    videoFile2.value = input.files[0]
  }
}

function handleDropHalf1(event: DragEvent) {
  dragOverHalf1.value = false
  if (event.dataTransfer?.files[0]) {
    videoFile1.value = event.dataTransfer.files[0]
  }
}

function handleDropHalf2(event: DragEvent) {
  dragOverHalf2.value = false
  if (event.dataTransfer?.files[0]) {
    videoFile2.value = event.dataTransfer.files[0]
  }
}

async function handleUpload() {
  if (!canUpload.value) return

  try {
    uploading.value = true
    uploadProgress.value = 0

    // 1. Créer job
    uploadStep.value = 'Création du job...'
    uploadMessage.value = 'Initialisation de la session d\'upload'
    uploadProgress.value = 10
    const job = await createUploadJob(matchName.value)
    jobId.value = job.job_id
    jobStatus.value = 'uploading'

    // 2. Upload vidéo 1
    uploadStep.value = 'Upload mi-temps 1...'
    uploadMessage.value = `Upload de ${videoFile1.value!.name} (${formatFileSize(videoFile1.value!.size)})`
    uploadProgress.value = 25
    await uploadVideo(jobId.value, 1, videoFile1.value!)

    // 3. Upload vidéo 2
    uploadStep.value = 'Upload mi-temps 2...'
    uploadMessage.value = `Upload de ${videoFile2.value!.name} (${formatFileSize(videoFile2.value!.size)})`
    uploadProgress.value = 50
    await uploadVideo(jobId.value, 2, videoFile2.value!)

    // 4. Finaliser
    uploadStep.value = 'Finalisation de l\'upload...'
    uploadMessage.value = 'Préparation des fichiers'
    uploadProgress.value = 65
    const finalized = await finalizeUpload(jobId.value)
    matchDir.value = finalized.match_dir || ''
    jobStatus.value = 'processing'

    // 5. Extraire features
    uploadStep.value = 'Extraction des features ResNET...'
    uploadMessage.value = 'Cela peut prendre 5-15 minutes selon votre configuration'
    uploadProgress.value = 80
    await extractFeatures(jobId.value)

    uploadProgress.value = 100
    jobStatus.value = 'done'
    uploadMessage.value = 'Terminé ! Vous pouvez maintenant analyser le match'

    Notify.create({
      type: 'positive',
      message: 'Upload et extraction complétés avec succès !',
      position: 'top'
    })
  } catch (error) {
    jobStatus.value = 'error'
    uploadMessage.value = `Erreur: ${error instanceof Error ? error.message : String(error)}`
    Notify.create({
      type: 'negative',
      message: `Erreur: ${error instanceof Error ? error.message : String(error)}`,
      position: 'top'
    })
  } finally {
    uploading.value = false
  }
}

async function refreshJobStatus() {
  if (!jobId.value) return
  try {
    const status = await getUploadStatus(jobId.value)
    jobStatus.value = status.status
    if (status.features_status === 'done') {
      matchDir.value = status.match_dir || matchDir.value
    }
  } catch (error) {
    Notify.create({
      type: 'negative',
      message: 'Erreur lors de la récupération du statut',
      position: 'top'
    })
  }
}

function handleAnalyze() {
  if (!matchDir.value) return
  // Émettre un événement ou rediriger vers l'analyse
  emit('analyze', {
    match_dir: matchDir.value,
    checkpoint: selectedCheckpoint.value,
    score_threshold: scoreThreshold.value
  })
}

function copyJobId() {
  navigator.clipboard.writeText(jobId.value)
  Notify.create({
    type: 'positive',
    message: 'Job ID copié',
    position: 'top'
  })
}

function reset() {
  matchName.value = ''
  videoFile1.value = null
  videoFile2.value = null
  featuresFile1.value = null
  featuresFile2.value = null
  videoOptFile1.value = null
  videoOptFile2.value = null
  uploading.value = false
  uploadProgress.value = 0
  uploadStep.value = ''
  uploadMessage.value = ''
  jobId.value = ''
  jobStatus.value = ''
  matchDir.value = ''
  scoreThreshold.value = 0.3
}

// Méthodes pour le mode features
function selectFileFeatures1() {
  inputFeatures1.value?.click()
}

function selectFileFeatures2() {
  inputFeatures2.value?.click()
}

function handleFileSelectFeatures1(event: Event) {
  const files = (event.target as HTMLInputElement).files
  if (files?.[0]) {
    featuresFile1.value = files[0]
  }
}

function handleFileSelectFeatures2(event: Event) {
  const files = (event.target as HTMLInputElement).files
  if (files?.[0]) {
    featuresFile2.value = files[0]
  }
}

function handleDropFeatures1(event: DragEvent) {
  dragOverFeatures1.value = false
  if (event.dataTransfer?.files[0]) {
    featuresFile1.value = event.dataTransfer.files[0]
  }
}

function handleDropFeatures2(event: DragEvent) {
  dragOverFeatures2.value = false
  if (event.dataTransfer?.files[0]) {
    featuresFile2.value = event.dataTransfer.files[0]
  }
}

function selectVideoOpt1() { inputVideoOpt1.value?.click() }
function selectVideoOpt2() { inputVideoOpt2.value?.click() }

function handleFileVideoOpt1(event: Event) {
  const files = (event.target as HTMLInputElement).files
  if (files?.[0]) videoOptFile1.value = files[0]
}

function handleFileVideoOpt2(event: Event) {
  const files = (event.target as HTMLInputElement).files
  if (files?.[0]) videoOptFile2.value = files[0]
}

function handleDropVideo1(event: DragEvent) {
  dragOverVideo1.value = false
  if (event.dataTransfer?.files[0]) videoOptFile1.value = event.dataTransfer.files[0]
}

function handleDropVideo2(event: DragEvent) {
  dragOverVideo2.value = false
  if (event.dataTransfer?.files[0]) videoOptFile2.value = event.dataTransfer.files[0]
}

async function handleFeaturesImport() {
  if (!canImportFeatures.value) return

  try {
    uploading.value = true
    uploadProgress.value = 0

    // 1. Créer job
    uploadStep.value = 'Création du job...'
    uploadMessage.value = 'Initialisation de la session d\'import'
    uploadProgress.value = 10
    const job = await createUploadJob(matchName.value)
    jobId.value = job.job_id
    jobStatus.value = 'uploading'

    // 2. Upload features 1
    uploadStep.value = 'Import features mi-temps 1...'
    uploadMessage.value = `Import de ${featuresFile1.value!.name} (${formatFileSize(featuresFile1.value!.size)})`
    uploadProgress.value = 40
    await uploadFeaturesFile(jobId.value, 1, featuresFile1.value!)

    // 3. Upload features 2
    uploadStep.value = 'Import features mi-temps 2...'
    uploadMessage.value = `Import de ${featuresFile2.value!.name} (${formatFileSize(featuresFile2.value!.size)})`
    uploadProgress.value = 70
    await uploadFeaturesFile(jobId.value, 2, featuresFile2.value!)

    // 4. Upload vidéos optionnelles
    if (videoOptFile1.value) {
      uploadStep.value = 'Upload vidéo mi-temps 1...'
      uploadMessage.value = `Upload de ${videoOptFile1.value.name} (${formatFileSize(videoOptFile1.value.size)})`
      uploadProgress.value = 80
      await uploadVideo(jobId.value, 1, videoOptFile1.value)
    }
    if (videoOptFile2.value) {
      uploadStep.value = 'Upload vidéo mi-temps 2...'
      uploadMessage.value = `Upload de ${videoOptFile2.value.name} (${formatFileSize(videoOptFile2.value.size)})`
      uploadProgress.value = 90
      await uploadVideo(jobId.value, 2, videoOptFile2.value)
    }

    const status = await getUploadStatus(jobId.value)
    matchDir.value = status.match_dir || ''

    uploadProgress.value = 100
    jobStatus.value = 'done'
    uploadMessage.value = 'Terminé ! Les features sont prêtes pour l\'analyse'

    Notify.create({
      type: 'positive',
      message: 'Import des features complété avec succès !',
      position: 'top'
    })
  } catch (error) {
    jobStatus.value = 'error'
    uploadMessage.value = `Erreur: ${error instanceof Error ? error.message : String(error)}`
    Notify.create({
      type: 'negative',
      message: `Erreur: ${error instanceof Error ? error.message : String(error)}`,
      position: 'top'
    })
  } finally {
    uploading.value = false
  }
}

// Load checkpoints on mount
onMounted(async () => {
  try {
    const checkpoints = await listCheckpoints()
    checkpointOptions.value = checkpoints.map(cp => ({
      label: cp.name,
      value: cp.path
    }))
    if (checkpointOptions.value.length > 0) {
      selectedCheckpoint.value = checkpointOptions.value[0].value
    }
  } catch (error) {
    console.error('Erreur loading checkpoints:', error)
  }
})

// Emit
const emit = defineEmits<{
  analyze: [{ match_dir: string; checkpoint: string; score_threshold?: number }]
}>()
</script>

<style scoped lang="scss">
.upload-card {
  background: linear-gradient(135deg, rgba(0, 255, 255, 0.02), rgba(0, 200, 255, 0.02));

  .si-header-section {
    background: linear-gradient(90deg, rgba(0, 255, 255, 0.1), rgba(0, 200, 255, 0.05));
  }
}

.upload-zone {
  border: 2px dashed rgba(0, 255, 255, 0.3);
  border-radius: 8px;
  transition: all 0.3s ease;
  cursor: pointer;

  &:hover {
    border-color: rgba(0, 255, 255, 0.6);
    background: rgba(0, 255, 255, 0.05);
  }

  &.upload-zone-hover {
    border-color: rgb(0, 255, 255);
    background: rgba(0, 255, 255, 0.1);
  }

  &.upload-zone-success {
    border-color: rgb(76, 175, 80);
    background: rgba(76, 175, 80, 0.05);
  }
}

.mono {
  font-family: 'Monaco', 'Courier New', monospace;
  letter-spacing: 0.5px;
}
</style>
