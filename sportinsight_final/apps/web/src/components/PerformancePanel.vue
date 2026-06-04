<template>
  <q-dialog v-model="open" maximized>
    <q-card class="perf-dialog">
      <q-card-section class="row items-center justify-between q-py-sm q-px-lg">
        <div>
          <div class="text-overline text-blue-8">Performances</div>
          <div class="text-h6 text-weight-bold">{{ runId }}</div>
        </div>
        <q-btn flat round dense icon="close" v-close-popup />
      </q-card-section>

      <q-separator />

      <q-tabs v-model="tab" align="left" class="q-px-md" indicator-color="blue-8" active-color="blue-8" dense>
        <q-tab name="curves" icon="show_chart" label="Courbes d'entraînement" no-caps />
        <q-tab name="metrics" icon="leaderboard" label="Métriques test" no-caps />
      </q-tabs>

      <q-separator />

      <q-tab-panels v-model="tab" animated class="perf-panels">

        <!-- Courbes -->
        <q-tab-panel name="curves" class="q-pa-md">
          <div class="row q-col-gutter-md">
            <div class="col-12 col-lg-6">
              <div class="text-caption text-blue-grey-6 q-mb-xs">Loss entraînement / validation</div>
              <img :src="plotUrl('loss_curves.png')" class="plot-img" alt="Loss curves" />
            </div>
            <div class="col-12 col-lg-6">
              <div class="text-caption text-blue-grey-6 q-mb-xs">Composantes de la loss</div>
              <img :src="plotUrl('loss_components.png')" class="plot-img" alt="Loss components" />
            </div>
          </div>
        </q-tab-panel>

        <!-- Métriques -->
        <q-tab-panel name="metrics" class="q-pa-md q-gutter-lg">
          <div v-if="evalLoading" class="row items-center q-gutter-sm text-blue-grey-6">
            <q-spinner color="blue-8" /> Chargement…
          </div>
          <div v-else-if="evalError" class="text-red-7">{{ evalError }}</div>
          <template v-else-if="evalData">

            <!-- Résultats notre modèle -->
            <q-expansion-item
              default-opened
              icon="science"
              label="Notre modèle — split test interne"
              :caption="`${evalData.games_processed} matchs`"
              header-class="expansion-header"
              class="expansion-item"
            >
            <div class="q-pa-md">
              <div class="row q-gutter-md q-mb-md">
                <q-card flat bordered class="stat-card">
                  <q-card-section class="q-pa-sm text-center">
                    <div class="text-caption text-blue-grey-6">mAP loose (±5 s)</div>
                    <div class="text-h5 text-weight-bold text-blue-8">{{ pct(looseMap) }}</div>
                  </q-card-section>
                </q-card>
                <q-card flat bordered class="stat-card">
                  <q-card-section class="q-pa-sm text-center">
                    <div class="text-caption text-blue-grey-6">mAP tight (±1 s)</div>
                    <div class="text-h5 text-weight-bold text-indigo-8">{{ pct(tightMap) }}</div>
                  </q-card-section>
                </q-card>
              </div>

              <q-table
                :rows="classRows"
                :columns="classColumns"
                row-key="label"
                flat bordered dense
                :pagination="{ rowsPerPage: 20 }"
                hide-pagination
              >
                <template #body-cell-loose="{ row }">
                  <q-td>
                    <div class="row items-center q-gutter-xs no-wrap">
                      <q-linear-progress :value="row.loose" color="blue-8" class="ap-bar" />
                      <span class="text-caption mono">{{ pct(row.loose) }}</span>
                    </div>
                  </q-td>
                </template>
                <template #body-cell-tight="{ row }">
                  <q-td>
                    <div class="row items-center q-gutter-xs no-wrap">
                      <q-linear-progress :value="row.tight" color="indigo-8" class="ap-bar" />
                      <span class="text-caption mono">{{ pct(row.tight) }}</span>
                    </div>
                  </q-td>
                </template>
              </q-table>
            </div>
            </q-expansion-item>

            <!-- Résultats officiels SoccerNet API -->
            <q-expansion-item
              icon="verified"
              label="Évaluation officielle SoccerNet API — split test"
              :caption="officialLooseMap !== null ? `loose ${pct(officialLooseMap)} · tight ${pct(officialTightMap)}` : 'non généré'"
              header-class="expansion-header"
              class="expansion-item"
            >
            <div class="q-pa-md">
              <div v-if="officialLoading" class="row items-center q-gutter-sm text-blue-grey-6">
                <q-spinner color="blue-8" size="sm" /> Chargement…
              </div>
              <q-banner v-else-if="officialLooseMap === null" rounded class="banner-pending">
                <template #avatar><q-icon name="info" color="blue-8" /></template>
                Résultats non encore générés. Lance le script depuis le terminal :
                <div class="q-mt-xs">
                  <code>python scripts/evaluate_spotting_official.py --checkpoint runs/{{ runId }}/best_map.pt</code>
                </div>
              </q-banner>
              <template v-else>
                <div class="row q-gutter-md q-mb-md">
                  <q-card flat bordered class="stat-card">
                    <q-card-section class="q-pa-sm text-center">
                      <div class="text-caption text-blue-grey-6">mAP loose officiel</div>
                      <div class="text-h5 text-weight-bold text-blue-8">{{ pct(officialLooseMap) }}</div>
                    </q-card-section>
                  </q-card>
                  <q-card flat bordered class="stat-card">
                    <q-card-section class="q-pa-sm text-center">
                      <div class="text-caption text-blue-grey-6">mAP tight officiel</div>
                      <div class="text-h5 text-weight-bold text-indigo-8">{{ pct(officialTightMap) }}</div>
                    </q-card-section>
                  </q-card>
                </div>
                <q-table
                  :rows="officialClassRows"
                  :columns="classColumns"
                  row-key="label"
                  flat bordered dense
                  :pagination="{ rowsPerPage: 20 }"
                  hide-pagination
                >
                  <template #body-cell-loose="{ row }">
                    <q-td>
                      <div class="row items-center q-gutter-xs no-wrap">
                        <q-linear-progress :value="row.loose" color="blue-8" class="ap-bar" />
                        <span class="text-caption mono">{{ pct(row.loose) }}</span>
                      </div>
                    </q-td>
                  </template>
                  <template #body-cell-tight="{ row }">
                    <q-td>
                      <div class="row items-center q-gutter-xs no-wrap">
                        <q-linear-progress :value="row.tight" color="indigo-8" class="ap-bar" />
                        <span class="text-caption mono">{{ pct(row.tight) }}</span>
                      </div>
                    </q-td>
                  </template>
                </q-table>
              </template>
            </div>
            </q-expansion-item>

            <!-- Challenge 2022 -->
            <q-expansion-item
              icon="leaderboard"
              label="SoccerNet 2022 Challenge"
              caption="github.com/SoccerNet/sn-spotting · loose ±5 s · tight ±1 s"
              header-class="expansion-header"
              class="expansion-item"
            >
            <div class="q-pa-md">
              <q-table
                :rows="challenge2022Rows"
                :columns="challengeColumns"
                row-key="team"
                flat bordered dense
                :pagination="{ rowsPerPage: 25 }"
                hide-pagination
              >
                <template #body-cell-team="{ row }">
                  <q-td>
                    <span :class="row.highlight ? 'text-weight-bold text-blue-8' : ''">{{ row.team }}</span>
                    <q-chip v-if="row.highlight" dense square color="blue-8" text-color="white" size="xs" class="q-ml-xs">notre modèle</q-chip>
                  </q-td>
                </template>
                <template #body-cell-loose="{ row }">
                  <q-td>
                    <div class="row items-center q-gutter-xs no-wrap">
                      <q-linear-progress :value="row.loose / 100" color="blue-8" class="ap-bar" />
                      <span class="text-caption mono" :class="row.highlight ? 'text-weight-bold' : ''">{{ row.loose.toFixed(2) }} %</span>
                    </div>
                  </q-td>
                </template>
                <template #body-cell-tight="{ row }">
                  <q-td>
                    <div class="row items-center q-gutter-xs no-wrap">
                      <q-linear-progress :value="row.tight / 100" color="indigo-8" class="ap-bar" />
                      <span class="text-caption mono" :class="row.highlight ? 'text-weight-bold' : ''">{{ row.tight.toFixed(2) }} %</span>
                    </div>
                  </q-td>
                </template>
              </q-table>
            </div>
            </q-expansion-item>

            <!-- Challenge 2023 -->
            <q-expansion-item
              icon="leaderboard"
              label="SoccerNet 2023 Challenge"
              caption="Giancola et al., arXiv 2309.06006 · loose ±5 s · tight ±1 s"
              header-class="expansion-header"
              class="expansion-item"
            >
            <div class="q-pa-md">
              <q-table
                :rows="challengeRows"
                :columns="challengeColumns"
                row-key="team"
                flat bordered dense
                :pagination="{ rowsPerPage: 15 }"
                hide-pagination
              >
                <template #body-cell-team="{ row }">
                  <q-td>
                    <span :class="row.highlight ? 'text-weight-bold text-blue-8' : ''">{{ row.team }}</span>
                    <q-chip v-if="row.highlight" dense square color="blue-8" text-color="white" size="xs" class="q-ml-xs">notre modèle</q-chip>
                  </q-td>
                </template>
                <template #body-cell-loose="{ row }">
                  <q-td>
                    <div class="row items-center q-gutter-xs no-wrap">
                      <q-linear-progress :value="row.loose / 100" color="blue-8" class="ap-bar" />
                      <span class="text-caption mono" :class="row.highlight ? 'text-weight-bold' : ''">{{ row.loose.toFixed(2) }} %</span>
                    </div>
                  </q-td>
                </template>
                <template #body-cell-tight="{ row }">
                  <q-td>
                    <div class="row items-center q-gutter-xs no-wrap">
                      <q-linear-progress :value="row.tight / 100" color="indigo-8" class="ap-bar" />
                      <span class="text-caption mono" :class="row.highlight ? 'text-weight-bold' : ''">{{ row.tight.toFixed(2) }} %</span>
                    </div>
                  </q-td>
                </template>
              </q-table>
            </div>
            </q-expansion-item>

          </template>
        </q-tab-panel>

      </q-tab-panels>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getRunPlotUrl, getRunEval, getRunOfficialEval } from '../services/api'

const props = defineProps<{ runId: string }>()
const open = defineModel<boolean>({ required: true })

const tab = ref('curves')
const evalData = ref<Record<string, any> | null>(null)
const evalLoading = ref(false)
const evalError = ref<string | null>(null)
const officialData = ref<Record<string, any> | null>(null)
const officialLoading = ref(false)

function plotUrl(name: string): string {
  return getRunPlotUrl(props.runId, name)
}

function pct(v: number): string {
  return `${(v * 100).toFixed(1)} %`
}

const looseMap = computed(() => (evalData.value?.internal as any)?.loose_avg_mAP ?? 0)
const tightMap = computed(() => (evalData.value?.internal as any)?.tight_avg_mAP ?? 0)

const classRows = computed(() => {
  const internal = (evalData.value?.internal as any) ?? {}
  const loose = internal.loose_per_class_ap5s ?? {}
  const tight = internal.tight_per_class_ap1s ?? {}
  return Object.keys(loose).map((label) => ({
    label,
    loose: loose[label] ?? 0,
    tight: tight[label] ?? 0,
  })).sort((a, b) => b.loose - a.loose)
})

const classColumns = [
  { name: 'label', label: 'Classe', field: 'label', align: 'left' as const, sortable: true },
  { name: 'loose', label: 'AP loose (±5 s)', field: 'loose', align: 'left' as const, sortable: true },
  { name: 'tight', label: 'AP tight (±1 s)', field: 'tight', align: 'left' as const, sortable: true },
]

// Résultats officiels SoccerNet API (après exécution du script)
const officialLooseMap = computed(() => (officialData.value?.results as any)?.loose?.a_mAP ?? null)
const officialTightMap = computed(() => (officialData.value?.results as any)?.tight?.a_mAP ?? null)
const officialClassRows = computed(() => {
  const loose = (officialData.value?.results as any)?.loose?.a_mAP_per_class ?? {}
  const tight = (officialData.value?.results as any)?.tight?.a_mAP_per_class ?? {}
  return Object.keys(loose).map((label) => ({
    label,
    loose: loose[label] ?? 0,
    tight: tight[label] ?? 0,
  })).sort((a, b) => b.loose - a.loose)
})

// Résultats du SoccerNet 2022 Challenge (github.com/SoccerNet/sn-spotting)
const challenge2022Rows = computed(() => {
  const hasOfficial = officialLooseMap.value !== null
  const ourLoose = hasOfficial ? (officialLooseMap.value! * 100) : (looseMap.value * 100)
  const ourTight = hasOfficial ? (officialTightMap.value! * 100) : (tightMap.value * 100)
  return [
    { team: 'Yahoo Research',   loose: 78.05, tight: 67.81, highlight: false },
    { team: 'PTS',              loose: 73.62, tight: 66.73, highlight: false },
    { team: 'AS&RG',            loose: 72.83, tight: 64.88, highlight: false },
    { team: 'Rkrystal',        loose: 74.75, tight: 61.84, highlight: false },
    { team: 'mt_sdu_action',   loose: 69.86, tight: 62.26, highlight: false },
    { team: 'arturxe',         loose: 71.72, tight: 60.56, highlight: false },
    { team: 'cihe',            loose: 72.95, tight: 59.97, highlight: false },
    { team: 'GUC',             loose: 70.49, tight: 58.71, highlight: false },
    { team: 'abcdefg',         loose: 67.88, tight: 56.07, highlight: false },
    { team: 'intro-and inter', loose: 67.75, tight: 53.97, highlight: false },
    { team: 'memory',          loose: 67.15, tight: 53.03, highlight: false },
    { team: 'stargazer',       loose: 60.86, tight: 52.04, highlight: false },
    { team: 'heaven',          loose: 60.88, tight: 51.85, highlight: false },
    { team: 'Baseline (2022)', loose: 74.84, tight: 49.56, highlight: false },
    { team: 'lczazu',          loose: 60.86, tight: 49.56, highlight: false },
    { team: 'zqing',           loose: 66.66, tight: 47.54, highlight: false },
    { team: 'welkin',          loose: 50.90, tight: 42.74, highlight: false },
    { team: 'DUT',             loose: 68.40, tight: 40.65, highlight: false },
    { team: 'sshinde5',        loose: 51.36, tight: 36.71, highlight: false },
    { team: 'SIT',             loose: 29.92, tight: 21.60, highlight: false },
    { team: props.runId,       loose: +ourLoose.toFixed(2), tight: +ourTight.toFixed(2), highlight: true },
  ].sort((a, b) => b.tight - a.tight)
})

// Résultats du SoccerNet 2023 Challenge (arXiv 2309.06006, Table 1)
// + notre modèle (résultats officiels SoccerNet API si disponibles, sinon internes)
const challengeRows = computed(() => {
  const hasOfficial = officialLooseMap.value !== null
  const ourLoose = hasOfficial ? (officialLooseMap.value! * 100) : (looseMap.value * 100)
  const ourTight = hasOfficial ? (officialTightMap.value! * 100) : (tightMap.value * 100)
  return [
    { team: 'SDU_VSISLABS',      loose: 78.56, tight: 71.31, highlight: false },
    { team: 'mt_player',         loose: 78.79, tight: 71.10, highlight: false },
    { team: 'ASTRAS',            loose: 79.21, tight: 70.10, highlight: false },
    { team: 'team_ws_action',    loose: 76.95, tight: 69.17, highlight: false },
    { team: 'CEA LVAS',          loose: 73.98, tight: 68.38, highlight: false },
    { team: 'Baseline (E2E)',    loose: 78.06, tight: 68.33, highlight: false },
    { team: 'DVP',               loose: 73.61, tight: 66.95, highlight: false },
    { team: 'JAMY2 (AF_GRU)',    loose: 63.12, tight: 51.97, highlight: false },
    { team: 'tyru (GRU_CALF)',   loose: 62.88, tight: 51.38, highlight: false },
    { team: 'JAMY (LocPoint)',   loose: 61.80, tight: 45.83, highlight: false },
    { team: props.runId,         loose: +ourLoose.toFixed(2), tight: +ourTight.toFixed(2), highlight: true },
  ].sort((a, b) => b.tight - a.tight)
})

const challengeColumns = [
  { name: 'team',  label: 'Équipe / Modèle', field: 'team',  align: 'left' as const },
  { name: 'loose', label: 'mAP loose (±5 s)', field: 'loose', align: 'left' as const, sortable: true },
  { name: 'tight', label: 'mAP tight (±1 s)', field: 'tight', align: 'left' as const, sortable: true },
]

watch(tab, async (t) => {
  if (t !== 'metrics') return
  if (!evalData.value && !evalLoading.value) {
    evalLoading.value = true
    evalError.value = null
    try {
      evalData.value = await getRunEval(props.runId)
    } catch (e) {
      evalError.value = e instanceof Error ? e.message : 'Erreur de chargement'
    } finally {
      evalLoading.value = false
    }
  }
  if (!officialData.value && !officialLoading.value) {
    officialLoading.value = true
    try {
      officialData.value = await getRunOfficialEval(props.runId, 'test')
    } catch {
      // pas encore généré — silencieux
    } finally {
      officialLoading.value = false
    }
  }
})
</script>

<style scoped>
.perf-dialog {
  background: #f8fafc;
}
.perf-panels {
  background: transparent;
  height: calc(100vh - 120px);
  overflow-y: auto;
}
.plot-img {
  width: 100%;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.10);
}
.stat-card {
  min-width: 160px;
  border-radius: 12px;
}
.ap-bar {
  width: 80px;
  height: 6px;
  border-radius: 4px;
}
.mono {
  font-family: ui-monospace, monospace;
}
.expansion-item {
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 10px;
  margin-bottom: 8px;
  overflow: hidden;
}
:deep(.expansion-header) {
  background: rgba(224, 242, 254, 0.50);
  border-radius: 10px;
}
:deep(.expansion-header:hover) {
  background: rgba(186, 230, 253, 0.60);
}
.banner-pending {
  background: rgba(224, 242, 254, 0.70);
  color: #0c4a6e;
  border: 1px solid rgba(2, 132, 199, 0.22);
}
.banner-pending code {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  background: rgba(186, 230, 253, 0.60);
  padding: 2px 6px;
  border-radius: 4px;
}
</style>
