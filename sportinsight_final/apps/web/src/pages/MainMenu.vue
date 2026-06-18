<template>
  <q-layout view="hHh lpR fFf">
    <q-header class="si-header">
      <q-toolbar class="q-px-lg">
        <q-toolbar-title>
          <span class="text-weight-bold">SportInsight</span>
          <span class="text-blue-2"> AI</span>
        </q-toolbar-title>
        <q-badge color="cyan" text-color="black">Jalon 5</q-badge>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-page class="q-pa-md">
        <!-- Menu principal -->
        <div v-if="currentPage === 'menu'" class="menu-container">
          <q-card class="menu-card q-mb-lg">
            <q-card-section class="text-center q-py-xl">
              <div class="text-h3 q-mb-md text-weight-bold">
                <span>SportInsight</span>
                <span class="text-cyan"> AI</span>
              </div>
              <div class="text-subtitle1 text-grey-7">
                Analyse intelligente de matchs de football
              </div>
            </q-card-section>
          </q-card>

          <div class="row q-col-gutter-lg q-mb-lg">
            <!-- Option 1: Analyser -->
            <div class="col-12 col-md-6">
              <q-card
                class="option-card option-card-analyze"
                :class="{ 'option-card-hover': hoveredOption === 'analyze' }"
                @mouseover="hoveredOption = 'analyze'"
                @mouseleave="hoveredOption = null"
                @click="handleSelectOption('analyze')"
              >
                <q-card-section class="text-center q-py-xl">
                  <q-icon name="analytics" size="4em" class="text-cyan q-mb-md" />
                  <div class="text-h6 text-weight-bold q-mb-md">Analyser un match</div>
                  <div class="text-body2 text-grey-7">
                    Analysez des matchs de SoccerNet ou des matchs précédemment uploadés
                  </div>
                  <q-btn
                    flat
                    label="Continuer"
                    color="cyan"
                    text-color="black"
                    icon-right="arrow_forward"
                    class="q-mt-lg"
                  />
                </q-card-section>
              </q-card>
            </div>

            <!-- Option 2: Uploader -->
            <div class="col-12 col-md-6">
              <q-card
                class="option-card option-card-upload"
                :class="{ 'option-card-hover': hoveredOption === 'upload' }"
                @mouseover="hoveredOption = 'upload'"
                @mouseleave="hoveredOption = null"
                @click="handleSelectOption('upload')"
              >
                <q-card-section class="text-center q-py-xl">
                  <q-icon name="cloud_upload" size="4em" class="text-orange q-mb-md" />
                  <div class="text-h6 text-weight-bold q-mb-md">Uploader une vidéo</div>
                  <div class="text-body2 text-grey-7">
                    Importez vos propres vidéos (mi-temps 1 et 2) pour analyse
                  </div>
                  <q-btn
                    flat
                    label="Continuer"
                    color="orange"
                    text-color="white"
                    icon-right="arrow_forward"
                    class="q-mt-lg"
                  />
                </q-card-section>
              </q-card>
            </div>
          </div>

          <!-- Informations -->
          <q-card class="info-card">
            <q-card-section>
              <div class="row q-col-gutter-md">
                <div class="col-12 col-md-4">
                  <div class="text-center">
                    <q-icon name="sports_soccer" size="2.5em" class="text-cyan q-mb-sm" />
                    <div class="text-body2 text-weight-bold">Modèles pré-entraînés</div>
                    <div class="text-caption text-grey-7">Détection d'événements précise</div>
                  </div>
                </div>
                <div class="col-12 col-md-4">
                  <div class="text-center">
                    <q-icon name="cloud_done" size="2.5em" class="text-orange q-mb-sm" />
                    <div class="text-body2 text-weight-bold">Upload sécurisé</div>
                    <div class="text-caption text-grey-7">Vos vidéos restent locales</div>
                  </div>
                </div>
                <div class="col-12 col-md-4">
                  <div class="text-center">
                    <q-icon name="speed" size="2.5em" class="text-green q-mb-sm" />
                    <div class="text-body2 text-weight-bold">Rapide et efficace</div>
                    <div class="text-caption text-grey-7">Résultats en quelques minutes</div>
                  </div>
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Page Analyser -->
        <div v-else-if="currentPage === 'analyze'">
          <div class="q-mb-md">
            <q-btn
              flat
              icon="arrow_back"
              label="Retour au menu"
              @click="handleBackToMenu"
            />
          </div>
          <AnalystRoom :initialMatchDir="uploadedMatchDir" :initialCheckpoint="uploadedCheckpoint" :initialScoreThreshold="uploadedScoreThreshold" />
        </div>

        <!-- Page Uploader -->
        <div v-else-if="currentPage === 'upload'">
          <div class="q-mb-md">
            <q-btn
              flat
              icon="arrow_back"
              label="Retour au menu"
              @click="currentPage = 'menu'"
            />
          </div>
          <VideoUploader @analyze="handleAnalyzeUploaded" />
        </div>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AnalystRoom from './AnalystRoom.vue'
import VideoUploader from '../components/VideoUploader.vue'

type PageType = 'menu' | 'analyze' | 'upload'

const currentPage = ref<PageType>('menu')
const hoveredOption = ref<string | null>(null)
const uploadedMatchDir = ref<string>('')
const uploadedCheckpoint = ref<string>('')
const uploadedScoreThreshold = ref<number>(0.3)

function handleSelectOption(option: string) {
  if (option === 'analyze') {
    uploadedMatchDir.value = ''
    uploadedCheckpoint.value = ''
    uploadedScoreThreshold.value = 0.3
    currentPage.value = 'analyze'
  } else if (option === 'upload') {
    currentPage.value = 'upload'
  }
}

function handleAnalyzeUploaded(data: { match_dir: string; checkpoint: string; score_threshold?: number }) {
  // Stocker le match_dir, checkpoint et score_threshold
  uploadedMatchDir.value = data.match_dir
  uploadedCheckpoint.value = data.checkpoint
  uploadedScoreThreshold.value = data.score_threshold ?? 0.3
  // Naviguer vers l'analyse
  currentPage.value = 'analyze'
}

function handleBackToMenu() {
  // Réinitialiser les données uploadées
  uploadedMatchDir.value = ''
  uploadedCheckpoint.value = ''
  uploadedScoreThreshold.value = 0.3
  currentPage.value = 'menu'
}
</script>

<style scoped lang="scss">
.menu-container {
  max-width: 1200px;
  margin: 0 auto;
}

.menu-card {
  background: linear-gradient(135deg, rgba(0, 255, 255, 0.1), rgba(0, 200, 255, 0.05));
  border: 1px solid rgba(0, 255, 255, 0.2);
}

.option-card {
  border: 1px solid rgba(0, 255, 255, 0.1);
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    border-color: rgba(0, 255, 255, 0.3);
  }

  &.option-card-analyze {
    &.option-card-hover {
      border-color: rgb(0, 188, 212);
      box-shadow: 0 8px 24px rgba(0, 188, 212, 0.15);
      transform: translateY(-4px);
    }
  }

  &.option-card-upload {
    &.option-card-hover {
      border-color: rgb(255, 152, 0);
      box-shadow: 0 8px 24px rgba(255, 152, 0, 0.15);
      transform: translateY(-4px);
    }
  }
}

.info-card {
  background: rgba(0, 255, 255, 0.02);
  border: 1px solid rgba(0, 255, 255, 0.1);
}
</style>
