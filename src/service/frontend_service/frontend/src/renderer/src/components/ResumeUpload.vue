<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{
  sessionId: string
}>()

const emit = defineEmits(['questionsReady'])

const resumeFile = ref<File | null>(null)
const uploading = ref(false)
const analyzing = ref(false)
const uploaded = ref(false)
const resumeFilename = ref('')
const questions = ref<any[]>([])
const questionsReady = ref(false)
const error = ref('')

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    resumeFile.value = input.files[0]
    error.value = ''
  }
}

async function uploadResume() {
  if (!resumeFile.value) return
  uploading.value = true
  error.value = ''

  try {
    const formData = new FormData()
    formData.append('file', resumeFile.value)

    const resp = await fetch(`/openavatarinterview/sessions/${props.sessionId}/resume`, {
      method: 'POST',
      body: formData,
    })

    if (!resp.ok) {
      throw new Error(`上传失败: ${resp.status}`)
    }

    const data = await resp.json()
    uploaded.value = true
    resumeFilename.value = data.resume_filename || resumeFile.value.name
    analyzing.value = true

    // Poll for questions to be ready
    await pollQuestions()
  } catch (e: any) {
    error.value = e.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function pollQuestions() {
  const maxAttempts = 30
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, 2000))
    try {
      const resp = await fetch(`/openavatarinterview/sessions/${props.sessionId}/questions`)
      if (resp.ok) {
        const data = await resp.json()
        if (data.questions && data.questions.length > 0) {
          questions.value = data.questions
          questionsReady.value = true
          analyzing.value = false
          emit('questionsReady', data.questions)
          return
        }
      }
    } catch {}
  }
  analyzing.value = false
  error.value = '分析超时，请稍后刷新查看'
}

function skipUpload() {
  emit('questionsReady', [])
}
</script>

<template>
  <div class="resume-upload">
    <div class="resume-card">
      <h3 class="resume-title">上传简历开始面试</h3>
      <p class="resume-desc">支持 PDF、Word、TXT、Markdown 格式</p>

      <div v-if="!uploaded" class="upload-area">
        <label class="file-label" for="resume-input">
          <div class="file-drop">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span v-if="resumeFile" class="file-name">{{ resumeFile.name }}</span>
            <span v-else class="file-hint">点击选择文件</span>
          </div>
        </label>
        <input
          id="resume-input"
          type="file"
          accept=".pdf,.docx,.txt,.md"
          style="display: none"
          @change="onFileChange"
        />

        <div class="btn-row">
          <button class="upload-btn" :disabled="!resumeFile || uploading" @click="uploadResume">
            {{ uploading ? '上传中...' : '上传并分析' }}
          </button>
          <button class="skip-btn" @click="skipUpload">跳过，直接开始</button>
        </div>
      </div>

      <div v-else-if="analyzing" class="analyzing">
        <div class="spinner" />
        <span>正在分析简历并生成面试问题...</span>
      </div>

      <div v-else-if="questionsReady" class="questions-list">
        <div class="questions-header">
          <span class="questions-tag">已生成 {{ questions.length }} 个面试问题</span>
        </div>
        <div v-for="(q, i) in questions" :key="i" class="question-item">
          <span class="q-index">{{ i + 1 }}</span>
          <div class="q-content">
            <div class="q-text">{{ q.question }}</div>
            <div class="q-meta">
              <span class="q-category">{{ q.category }}</span>
              <span class="q-skill">{{ q.target_skill }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="error" class="error-msg">{{ error }}</div>
    </div>
  </div>
</template>

<style scoped lang="less">
.resume-upload {
  width: 100%;
  display: flex;
  justify-content: center;
  padding: 0 70px;
}

.resume-card {
  width: 100%;
  max-width: 480px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 20px;
  padding: 28px 24px;
  box-shadow: 0 4px 20px rgba(124, 58, 237, 0.06), 0 1px 4px rgba(0, 0, 0, 0.04);
}

.resume-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 6px;
  text-align: center;
}

.resume-desc {
  font-size: 13px;
  color: #94a3b8;
  margin: 0 0 20px;
  text-align: center;
}

.upload-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.file-label {
  cursor: pointer;
}

.file-drop {
  border: 2px dashed rgba(124, 58, 237, 0.2);
  border-radius: 14px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;

  &:hover {
    border-color: rgba(124, 58, 237, 0.4);
    background: rgba(124, 58, 237, 0.02);
  }
}

.file-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.file-hint {
  font-size: 13px;
  color: #94a3b8;
}

.btn-row {
  display: flex;
  gap: 10px;
}

.upload-btn {
  flex: 1;
  height: 42px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.skip-btn {
  height: 42px;
  padding: 0 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
  color: #64748b;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #f8fafc;
    color: #334155;
  }
}

.analyzing {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 20px 0;
  color: #7c3aed;
  font-size: 14px;
  font-weight: 500;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(124, 58, 237, 0.2);
  border-top-color: #7c3aed;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.questions-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;

  &::-webkit-scrollbar {
    width: 3px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 3px;
  }
}

.questions-header {
  margin-bottom: 4px;
}

.questions-tag {
  font-size: 13px;
  font-weight: 600;
  color: #7c3aed;
  background: rgba(124, 58, 237, 0.08);
  padding: 4px 10px;
  border-radius: 8px;
}

.question-item {
  display: flex;
  gap: 10px;
  padding: 10px;
  background: rgba(248, 250, 252, 0.8);
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.5);
}

.q-index {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.q-content {
  flex: 1;
  min-width: 0;
}

.q-text {
  font-size: 13px;
  color: #1e293b;
  line-height: 1.5;
  margin-bottom: 4px;
}

.q-meta {
  display: flex;
  gap: 6px;
}

.q-category,
.q-skill {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
}

.q-category {
  background: rgba(124, 58, 237, 0.08);
  color: #7c3aed;
}

.q-skill {
  background: rgba(16, 185, 129, 0.08);
  color: #059669;
}

.error-msg {
  margin-top: 12px;
  padding: 10px;
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: 10px;
  color: #dc2626;
  font-size: 13px;
  text-align: center;
}
</style>
