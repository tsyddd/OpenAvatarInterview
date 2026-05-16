<script setup lang="ts">
import { ref, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useAppStore } from '@/store/app'

const appStore = useAppStore()
const { resumeList, selectedResumeId } = storeToRefs(appStore)

const showImport = ref(false)
const uploadFile = ref<File | null>(null)
const uploading = ref(false)
const analyzing = ref(false)
const uploadError = ref('')
const uploadSessionId = ref('')

const selectedResume = computed(() => {
  if (!selectedResumeId.value) return null
  return resumeList.value.find((r) => r.id === selectedResumeId.value) || null
})

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    uploadFile.value = input.files[0]
    uploadError.value = ''
  }
}

function closeImport() {
  showImport.value = false
  uploadFile.value = null
  uploadError.value = ''
  uploading.value = false
  analyzing.value = false
}

async function uploadResume() {
  if (!uploadFile.value) return
  uploading.value = true
  uploadError.value = ''

  const sessionId = crypto.randomUUID ? crypto.randomUUID() : Date.now().toString()
  uploadSessionId.value = sessionId

  try {
    const formData = new FormData()
    formData.append('file', uploadFile.value)

    const resp = await fetch(`/openavatarinterview/sessions/${sessionId}/resume`, {
      method: 'POST',
      body: formData,
    })
    if (!resp.ok) throw new Error(`上传失败: ${resp.status}`)
    const data = await resp.json()

    const filename = data.resume_filename || uploadFile.value.name
    analyzing.value = true

    // Poll for questions
    const questions = await pollQuestions(sessionId)

    appStore.addResume({
      id: sessionId,
      filename,
      uploadDate: new Date().toLocaleString('zh-CN'),
      questions,
    })

    closeImport()
  } catch (e: any) {
    uploadError.value = e.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function pollQuestions(sessionId: string): Promise<any[]> {
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 2000))
    try {
      const resp = await fetch(`/openavatarinterview/sessions/${sessionId}/questions`)
      if (resp.ok) {
        const data = await resp.json()
        if (data.questions && data.questions.length > 0) {
          return data.questions
        }
      }
    } catch {}
  }
  return []
}

function selectResume(id: string) {
  appStore.selectResume(id)
}

function startInterview() {
  if (selectedResumeId.value) {
    appStore.startInterview(selectedResumeId.value)
  }
}

function removeResume(id: string) {
  appStore.removeResume(id)
}
</script>

<template>
  <div class="home-container">
    <!-- Left Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2 class="sidebar-title">简历管理</h2>
        <button class="import-btn" @click="showImport = true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>导入简历</span>
        </button>
      </div>

      <!-- Resume List -->
      <div v-if="resumeList.length > 0" class="resume-list">
        <div
          v-for="resume in resumeList"
          :key="resume.id"
          :class="['resume-card', { active: resume.id === selectedResumeId }]"
          @click="selectResume(resume.id)"
        >
          <div class="resume-card-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
            <div class="resume-card-info">
              <span class="resume-filename">{{ resume.filename }}</span>
              <span class="resume-date">{{ resume.uploadDate }}</span>
            </div>
            <button class="delete-btn" @click.stop="removeResume(resume.id)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
            </button>
          </div>
          <div class="resume-card-tags">
            <span class="tag">分析完成</span>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="sidebar-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#c4b5fd" stroke-width="1">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        <p>暂无简历，请点击上方按钮导入</p>
      </div>
    </aside>

    <!-- Right Main Area -->
    <main class="main-area">
      <template v-if="selectedResume">
        <div class="welcome-card">
          <div class="resume-info-card">
            <div class="resume-info-header">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <div>
                <h3>{{ selectedResume.filename }}</h3>
                <span class="resume-date-text">{{ selectedResume.uploadDate }}</span>
              </div>
            </div>
            <div class="resume-status">
              <span class="status-badge">简历分析完成</span>
            </div>
          </div>

          <button class="start-btn" @click="startInterview">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            <span>模拟面试</span>
          </button>
        </div>
      </template>

      <template v-else>
        <div class="empty-state">
          <div class="empty-icon">
            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#c4b5fd" stroke-width="0.8">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
          </div>
          <h2 class="empty-title">请先导入并选择一份简历</h2>
          <p class="empty-desc">导入简历后，系统将自动生成面试问题，点击"模拟面试"开始对话</p>
        </div>
      </template>
    </main>

    <!-- Import Modal Overlay -->
    <Teleport to="body">
      <div v-if="showImport" class="modal-overlay" @click.self="closeImport">
        <div class="modal-card">
          <div class="modal-header">
            <h3>导入简历</h3>
            <button class="modal-close" @click="closeImport">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <p class="modal-desc">支持 PDF、Word、TXT、Markdown 格式</p>

            <label for="home-resume-input" class="file-drop-zone" :class="{ hasFile: uploadFile }">
              <div v-if="uploadFile" class="file-selected">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <span class="file-name">{{ uploadFile.name }}</span>
                <span class="file-change">点击更换</span>
              </div>
              <div v-else class="file-placeholder">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
                <span class="upload-hint">点击选择文件</span>
              </div>
            </label>
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              style="display: none"
              id="home-resume-input"
              @change="onFileChange"
            />

            <!-- Progress -->
            <div v-if="uploading && !analyzing" class="upload-status">
              <div class="spinner" />
              <span>上传中...</span>
            </div>
            <div v-if="analyzing" class="upload-status">
              <div class="spinner" />
              <span>正在分析简历并生成面试问题...</span>
            </div>

            <div v-if="uploadError" class="error-text">{{ uploadError }}</div>

            <div class="modal-actions">
              <button class="cancel-btn" @click="closeImport">取消</button>
              <button class="confirm-btn" :disabled="!uploadFile || uploading" @click="uploadResume">
                {{ uploading ? '上传中...' : '上传并分析' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style lang="less" scoped>
.home-container {
  display: flex;
  height: 100vh;
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 30%, #e0e7ff 60%, #dbeafe 100%);
  overflow: hidden;
}

/* ── Sidebar ── */
.sidebar {
  width: 320px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(124, 58, 237, 0.08);
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 20px 16px;
  border-bottom: 1px solid rgba(124, 58, 237, 0.06);
}

.sidebar-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.import-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 14px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
  }
}

/* ── Resume List ── */
.resume-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resume-card {
  padding: 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(226, 232, 240, 0.6);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: rgba(124, 58, 237, 0.2);
    background: rgba(255, 255, 255, 0.95);
  }

  &.active {
    border-color: rgba(124, 58, 237, 0.4);
    background: rgba(124, 58, 237, 0.04);
    box-shadow: 0 2px 8px rgba(124, 58, 237, 0.06);
  }
}

.resume-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #64748b;
}

.resume-card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.resume-filename {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.resume-date {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.delete-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;

  &:hover {
    background: rgba(239, 68, 68, 0.08);
    color: #dc2626;
  }
}

.resume-card-tags {
  margin-top: 8px;
}

.tag {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(124, 58, 237, 0.08);
  color: #7c3aed;
  font-weight: 500;
}

/* ── Sidebar Empty ── */
.sidebar-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
  gap: 12px;

  p { margin: 0; }
}

/* ── Main Area ── */
.main-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.welcome-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
  width: 100%;
  max-width: 560px;
}

.resume-info-card {
  width: 100%;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 20px;
  padding: 24px 28px;
  box-shadow: 0 4px 20px rgba(124, 58, 237, 0.06), 0 1px 4px rgba(0, 0, 0, 0.04);
}

.resume-info-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;

  h3 {
    font-size: 16px;
    font-weight: 700;
    color: #1e293b;
    margin: 0;
  }
}

.resume-date-text {
  font-size: 12px;
  color: #94a3b8;
}

.resume-status {
  margin-top: 8px;
}

.status-badge {
  font-size: 13px;
  font-weight: 600;
  color: #059669;
  background: rgba(16, 185, 129, 0.08);
  padding: 4px 10px;
  border-radius: 8px;
}

.start-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 220px;
  height: 56px;
  border: none;
  border-radius: 16px;
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 16px rgba(124, 58, 237, 0.25);

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(124, 58, 237, 0.35);
  }

  &:active {
    transform: translateY(0);
  }
}

/* ── Empty State ── */
.empty-state {
  text-align: center;
}

.empty-icon {
  margin-bottom: 20px;
}

.empty-title {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 8px;
}

.empty-desc {
  font-size: 14px;
  color: #94a3b8;
  margin: 0;
}

/* ── Modal ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  width: 420px;
  max-width: 90vw;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;

  h3 {
    font-size: 17px;
    font-weight: 700;
    color: #1e293b;
    margin: 0;
  }
}

.modal-close {
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
  transition: all 0.15s;

  &:hover {
    background: #f1f5f9;
    color: #475569;
  }
}

.modal-body {
  padding: 20px 24px 24px;
}

.modal-desc {
  font-size: 13px;
  color: #94a3b8;
  margin: 0 0 16px;
}

.file-drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px dashed rgba(124, 58, 237, 0.2);
  border-radius: 14px;
  padding: 28px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: rgba(124, 58, 237, 0.4);
    background: rgba(124, 58, 237, 0.02);
  }

  &.hasFile {
    border-color: rgba(124, 58, 237, 0.3);
    background: rgba(124, 58, 237, 0.03);
  }
}

.file-selected, .file-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.file-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.file-change {
  font-size: 11px;
  color: #7c3aed;
}

.upload-hint {
  font-size: 13px;
  color: #94a3b8;
}

.upload-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 16px;
  color: #7c3aed;
  font-size: 13px;
  font-weight: 500;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(124, 58, 237, 0.15);
  border-top-color: #7c3aed;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-text {
  margin-top: 12px;
  padding: 10px;
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: 10px;
  color: #dc2626;
  font-size: 13px;
  text-align: center;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.cancel-btn, .confirm-btn {
  flex: 1;
  height: 42px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;

  &:hover {
    background: #f8fafc;
  }
}

.confirm-btn {
  border: none;
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
  color: #fff;

  &:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}
</style>
