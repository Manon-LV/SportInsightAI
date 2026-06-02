<template>
  <q-card class="video-card" flat>
    <q-card-section class="row items-center justify-between q-pb-sm">
      <div>
        <div class="text-overline text-cyan-3">Extrait vidéo</div>
        <div class="text-subtitle1 text-weight-bold">
          {{ event ? `${event.label} · ${event.gameTime}` : 'Aucune action sélectionnée' }}
        </div>
      </div>
      <q-chip v-if="halfInfo?.available" dense square color="cyan-9" text-color="white">
        {{ halfInfo.name }}
      </q-chip>
    </q-card-section>

    <q-separator dark />

    <q-card-section v-if="!event" class="text-blue-grey-2">
      Sélectionne une action pour afficher l’extrait correspondant.
    </q-card-section>

    <q-card-section v-else-if="loading" class="row items-center q-gutter-sm text-blue-grey-2">
      <q-spinner color="cyan" />
      <span>Recherche des vidéos locales…</span>
    </q-card-section>

    <q-card-section v-else-if="!halfInfo?.available" class="q-gutter-sm">
      <q-banner rounded class="bg-blue-grey-10 text-blue-grey-2">
        <template #avatar>
          <q-icon name="videocam_off" color="amber" />
        </template>
        Aucune vidéo n’a été détectée pour la mi-temps {{ event.half }}.
        Ajoute les fichiers vidéo dans le dossier du match, par exemple
        <code>1.mp4</code>/<code>1.mkv</code> et <code>2.mp4</code>/<code>2.mkv</code>.
      </q-banner>
      <div class="text-caption text-blue-grey-4">
        Les features <code>.npy</code> suffisent pour l’inférence, mais elles ne permettent pas de reconstruire l’image vidéo.
      </div>
    </q-card-section>

    <q-card-section v-else class="q-gutter-md">
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

      <q-banner v-if="videoError" rounded class="bg-deep-orange-10 text-orange-1">
        <template #avatar>
          <q-icon name="warning" color="orange" />
        </template>
        Le navigateur n’arrive pas à lire ce format vidéo. Si le fichier est en <code>.mkv</code>, convertis-le en
        <code>.mp4</code> pour la démonstration.
      </q-banner>

      <div class="row q-col-gutter-sm">
        <div class="col-12 col-sm-6">
          <q-btn
            outline
            dense
            no-caps
            icon="replay_10"
            color="cyan"
            label="Revenir au début de l’extrait"
            class="full-width"
            @click="seekToClipStart"
          />
        </div>
        <div class="col-12 col-sm-6">
          <q-btn
            outline
            dense
            no-caps
            icon="play_arrow"
            color="amber"
            label="Lire autour de l’action"
            class="full-width"
            @click="playClip"
          />
        </div>
      </div>

      <div class="text-caption text-blue-grey-3">
        Fenêtre affichée : {{ clipStart.toFixed(1) }} s → {{ clipEnd.toFixed(1) }} s dans la mi-temps {{ event.half }}.
      </div>
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
    // Le navigateur peut refuser le seek tant que les métadonnées ne sont pas chargées.
  }
}

async function playClip() {
  await seekToClipStart()
  if (!videoRef.value) return
  try {
    await videoRef.value.play()
  } catch {
    Notify.create({ type: 'warning', message: 'Lecture automatique bloquée par le navigateur. Utilise le bouton lecture du lecteur vidéo.' })
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
  background: linear-gradient(135deg, rgba(8, 47, 73, 0.72), rgba(12, 18, 33, 0.94));
  border: 1px solid rgba(34, 211, 238, 0.24);
  border-radius: 18px;
  overflow: hidden;
}
.clip-video {
  width: 100%;
  min-height: 220px;
  max-height: 420px;
  border-radius: 14px;
  background: #020617;
  border: 1px solid rgba(148, 163, 184, 0.25);
}
code {
  color: #67e8f9;
  background: rgba(15, 23, 42, 0.9);
  padding: 0 4px;
  border-radius: 4px;
}
</style>
