<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { getInterviewAnalysis, getInterviewReportHtml, getInterviewSession, makeURL } from '@/apis'

const props = defineProps<{
  visible: boolean
  sessionId: string
}>()

const emit = defineEmits(['close'])

const loading = ref(false)
const error = ref('')
const reportHtmlReady = ref(false)
const analysis = ref<any>(null)
const session = ref<any>(null)
const pollTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const pdfDownloadUrl = computed(() => makeURL(`/openavatarinterview/sessions/${props.sessionId}/report/pdf`))
const reportHtmlUrl = computed(() => makeURL(`/openavatarinterview/sessions/${props.sessionId}/report/html`))

watch(() => props.visible, (v) => {
  if (v && props.sessionId) {
    void fetchReport()
  } else if (pollTimer.value) {
    clearTimeout(pollTimer.value)
    pollTimer.value = null
  }
})

onBeforeUnmount(() => {
  if (pollTimer.value) {
    clearTimeout(pollTimer.value)
    pollTimer.value = null
  }
})

async function fetchReport() {
  loading.value = true
  error.value = ''
  reportHtmlReady.value = false
  analysis.value = null
  session.value = null

  try {
    const [sessionResp, analysisResp, reportResp] = await Promise.all([
      getInterviewSession(props.sessionId),
      getInterviewAnalysis(props.sessionId),
      getInterviewReportHtml(props.sessionId),
    ])

    if (sessionResp.ok) {
      session.value = await sessionResp.json()
    }
    if (analysisResp.ok) {
      analysis.value = await analysisResp.json()
    }
    if (reportResp.ok) {
      reportHtmlReady.value = true
    }
    if (session.value?.report_status === 'failed') {
      error.value = session.value?.report_error || '报告生成失败'
    } else if (
      !analysis.value?.final_evaluation
      && !reportHtmlReady.value
      && ['pending', 'running'].includes(session.value?.report_status)
    ) {
      schedulePoll()
    } else if (!analysis.value?.final_evaluation && !reportHtmlReady.value) {
      error.value = '报告尚未生成，请稍后再试'
    }
  } catch (e: any) {
    error.value = '获取报告失败: ' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

function schedulePoll() {
  if (pollTimer.value) clearTimeout(pollTimer.value)
  pollTimer.value = setTimeout(() => {
    if (props.visible && props.sessionId) {
      fetchReport()
    }
  }, 2000)
}

function close() {
  emit('close')
}

function formatValue(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="report-overlay" @click.self="close">
      <div class="report-modal">
        <div class="report-header">
          <h2>面试报告</h2>
          <div class="report-actions">
            <a
              v-if="session?.report_pdf_ready"
              class="download-btn"
              :href="pdfDownloadUrl"
              target="_blank"
              rel="noopener noreferrer"
            >
              下载 PDF
            </a>
            <button class="close-btn" @click="close">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        <div class="report-body">
          <div v-if="loading" class="report-loading">
            <div class="spinner" />
            <span>正在加载报告...</span>
          </div>

          <div v-else-if="error" class="report-error">{{ error }}</div>

          <template v-else>
            <div
              v-if="['pending', 'running'].includes(session?.report_status) && !reportHtmlReady && !analysis?.final_evaluation"
              class="report-loading"
            >
              <div class="spinner" />
              <span>正在生成报告，请稍候...</span>
            </div>

            <!-- Evaluation Summary -->
            <div v-if="analysis?.final_evaluation" class="eval-section">
              <div class="eval-card">
                <h3>综合评估</h3>
                <div class="eval-content">{{ formatValue(analysis.final_evaluation) }}</div>
              </div>
            </div>

            <!-- Full Report -->
            <div v-if="reportHtmlReady" class="report-section">
              <h3>详细报告</h3>
              <iframe class="report-frame" :src="reportHtmlUrl" title="面试报告预览" />
            </div>

            <div v-if="!analysis?.final_evaluation && !reportHtmlReady" class="report-empty">
              {{ ['pending', 'running'].includes(session?.report_status) ? '报告生成中，请稍候...' : '报告尚未生成，请稍后再试' }}
            </div>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style lang="less" scoped>
.report-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.report-modal {
  width: 680px;
  max-width: 90vw;
  max-height: 90vh;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px;
  border-bottom: 1px solid #f1f5f9;

  h2 {
    font-size: 18px;
    font-weight: 700;
    color: #1e293b;
    margin: 0;
  }
}

.report-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.download-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 10px;
  background: #eff6ff;
  color: #2563eb;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;

  &:hover {
    background: #dbeafe;
  }
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background: #f1f5f9;
    color: #475569;
  }
}

.report-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
}

.report-frame {
  width: 100%;
  min-height: 960px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
}

.report-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 0;
  color: #7c3aed;
  font-size: 14px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(124, 58, 237, 0.15);
  border-top-color: #7c3aed;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.report-error {
  padding: 20px;
  text-align: center;
  color: #dc2626;
  font-size: 14px;
  background: rgba(239, 68, 68, 0.06);
  border-radius: 12px;
}

.eval-section {
  margin-bottom: 24px;
}

.eval-card {
  background: rgba(124, 58, 237, 0.04);
  border: 1px solid rgba(124, 58, 237, 0.08);
  border-radius: 14px;
  padding: 20px;

  h3 {
    font-size: 15px;
    font-weight: 700;
    color: #7c3aed;
    margin: 0 0 12px;
  }
}

.eval-content {
  font-size: 14px;
  color: #334155;
  line-height: 1.7;
  white-space: pre-wrap;
}

.report-section {
  h3 {
    font-size: 15px;
    font-weight: 700;
    color: #1e293b;
    margin: 0 0 12px;
  }
}

.report-content {
  font-size: 14px;
  color: #334155;
  line-height: 1.8;

  :deep(h1), :deep(h2), :deep(h3) {
    color: #1e293b;
    margin-top: 16px;
    margin-bottom: 8px;
  }
  :deep(p) { margin: 8px 0; }
  :deep(ul), :deep(ol) { padding-left: 20px; }
  :deep(li) { margin: 4px 0; }
  :deep(code) {
    background: #f1f5f9;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
  }
  :deep(strong) { color: #1e293b; }
}

.report-empty {
  text-align: center;
  padding: 40px 0;
  color: #94a3b8;
  font-size: 14px;
}
</style>
