<template>
  <q-card class="video-card" flat>
    <q-card-section v-if="!event" class="text-blue-grey-6 q-py-xs">
      Sélectionne une action pour afficher l'extrait correspondant.
    </q-card-section>

    <q-card-section v-else-if="loading" class="row items-center q-gutter-sm text-blue-grey-6 q-py-sm">
      <q-spinner color="amber-8" />
      <span>Recherche des vidéos locales…</span>
    </q-card-section>

    <q-card-section v-else-if="!halfInfo?.available" class="q-gutter-sm q-py-sm">
      <q-banner rounded class="banner-missing">
        <template #avatar>
          <q-icon name="videocam_off" color="amber-8" />
        </template>
        Aucune vidéo détectée pour la mi-temps {{ event.half }}.
        Ajoute <code>1.mp4</code>/<code>1.mkv</code> et <code>2.mp4</code>/<code>2.mkv</code> dans le dossier du match.
      </q-banner>
    </q-card-section>

    <q-card-section v-else class="q-gutter-sm q-py-sm">
      <video
        ref="videoRef"
        :key="videoKey"
        class="clip-video"
        :src="videoSrc"
        controls
        preload="metadata"
        @loadedmetadata="seekToClipStart"
        @error="videoError = true"
      />

      <q-banner v-if="videoError" rounded class="banner-error">
        <template #avatar>
          <q-icon name="warning" color="deep-orange-7" />
        </template>
        Impossible de lire ce format. Convertis le fichier en <code>.mp4</code>.
      </q-banner>

      <q-btn outline dense no-caps size="sm" icon="play_arrow" color="amber-8"
        label="Rejouer l'extrait" @click="playClip" />
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import { Notify } from 'quasar'
import { buildVideoUrl, getVideoAvailability } from '../services/api'
import type { EventPrediction, VideoAvailabilityResponse, VideoHalfInfo } from '../types/predictions'

const props = defineProps<{
  event: EventPrediction | null
  matchDir: string
  beforeSec?: number
  afterSec?: number
}>()

const availability = ref<VideoAvailabilityResponse | null>(null)
const loading = ref(false)
const videoRef = ref<HTMLVideoElement | null>(null)
const videoError = ref(false)

const before = computed(() => props.beforeSec ?? 10)
const after = computed(() => props.afterSec ?? 10)

const halfInfo = computed<VideoHalfInfo | null>(() => {
  if (!props.event || !availability.value) return null
  return availability.value.halves[String(props.event.half)] ?? null
})

const clipStart = computed(() => Math.max(0, (props.event?.timestamp ?? 0) - before.value))
const clipEnd = computed(() => Math.max(clipStart.value + 1, (props.event?.timestamp ?? 0) + after.value))

const videoSrc = computed(() => {
  if (!props.event || !halfInfo.value?.available) return ''
  return buildVideoUrl(props.matchDir, props.event.half, clipStart.value, clipEnd.value)
})

const videoKey = computed(() => {
  if (!props.event) return 'no-event'
  return `${props.matchDir}-${props.event.half}-${props.event.timestamp}-${props.event.label}`
})

async function refreshAvailability(matchDir: string) {
  if (!matchDir) return
  loading.value = true
  try {
    availability.value = await getVideoAvailability(matchDir)
  } catch (error) {
    availability.value = null
    const message = error instanceof Error ? error.message : 'Impossible de vérifier les vidéos locales.'
    Notify.create({ type: 'warning', message })
  } finally {
    loading.value = false
  }
}

async function seekToClipStart() {
  await nextTick()
  if (!videoRef.value) return
  try {
    videoRef.value.currentTime = clipStart.value
    videoError.value = false
  } catch {
    // seek possible seulement après chargement des métadonnées
  }
}

async function playClip() {
  await seekToClipStart()
  if (!videoRef.value) return
  try {
    await videoRef.value.play()
  } catch {
    Notify.create({ type: 'warning', message: 'Lecture automatique bloquée par le navigateur.' })
  }
}

watch(() => props.matchDir, refreshAvailability, { immediate: true })
watch(() => props.event, () => {
  videoError.value = false
  seekToClipStart()
})
</script>

<style scoped>
.video-card {
  background: transparent;
  border: none;
  border-radius: 14px;
  overflow: hidden;
}
.clip-video {
  width: 100%;
  max-height: 320px;
  border-radius: 10px;
  background: rgba(120, 53, 15, 0.06);
  border: 1px solid rgba(217, 119, 6, 0.20);
}
.banner-missing {
  background: rgba(254, 243, 199, 0.60);
  color: #78350f;
  border: 1px solid rgba(217, 119, 6, 0.22);
}
.banner-error {
  background: rgba(255, 237, 213, 0.70);
  color: #7c2d12;
  border: 1px solid rgba(234, 88, 12, 0.22);
}
code {
  color: #b45309;
  background: rgba(254, 243, 199, 0.80);
  padding: 0 4px;
  border-radius: 4px;
}
</style>
