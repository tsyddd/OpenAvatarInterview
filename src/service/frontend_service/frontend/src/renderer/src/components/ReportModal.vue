<script setup lang="ts">
import { ref, watch } from 'vue'
import { getInterviewAnalysis, getInterviewReport } from '@/apis'

const props = defineProps<{
  visible: boolean
  sessionId: string
}>()

const emit = defineEmits(['close'])

const loading = ref(false)
const error = ref('')
const reportMd = ref('')
const analysis = ref<any>(null)

watch(() => props.visible, (v) => {
  if (v && props.sessionId) {
    fetchReport()
  }
})

async function fetchReport() {
  loading.value = true
  error.value = ''
  reportMd.value = ''
  analysis.value = null

  try {
    const [analysisResp, reportResp] = await Promise.all([
      getInterviewAnalysis(props.sessionId),
      getInterviewReport(props.sessionId),
    ])

    if (analysisResp.ok) {
      analysis.value = await analysisResp.json()
    }
    if (reportResp.ok) {
      reportMd.value = await reportResp.text()
    }
    if (!analysis.value && !reportMd.value) {
      error.value = '报告尚未生成，请稍后再试'
    }
  } catch (e: any) {
    error.value = '获取报告失败: ' + (e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

function close() {
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="report-overlay" @click.self="close">
      <div class="report-modal">
        <div class="report-header">
          <h2>面试报告</h2>
          <button class="close-btn" @click="close">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div class="report-body">
          <div v-if="loading" class="report-loading">
            <div class="spinner" />
            <span>正在加载报告...</span>
          </div>

          <div v-else-if="error" class="report-error">{{ error }}</div>

          <template v-else>
            <!-- Evaluation Summary -->
            <div v-if="analysis?.final_evaluation" class="eval-section">
              <div class="eval-card">
                <h3>综合评估</h3>
                <div class="eval-content">{{ analysis.final_evaluation }}</div>
              </div>
            </div>

            <!-- Full Report -->
            <div v-if="reportMd" class="report-section">
              <h3>详细报告</h3>
              <div class="report-content markdown-body" v-html="reportMd"></div>
            </div>

            <div v-if="!analysis?.final_evaluation && !reportMd" class="report-empty">
              报告生成中，请稍候...
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
