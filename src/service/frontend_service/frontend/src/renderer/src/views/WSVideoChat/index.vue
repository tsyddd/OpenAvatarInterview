<template>
  <div ref="wrapRef" class="page-container">
    <div class="content-container">
      <div
        class="video-container"
      >
        <div
          v-show="hasCamera && !cameraOff"
          ref="localVideoContainerRef"
          :class="`local-video-container ${streamState === 'open' ? 'scaled' : ''}`"
        >
          <video
            ref="localVideoRef"
            class="local-video"
            autoplay
            muted
            playsinline
            :style="{
              visibility: cameraOff ? 'hidden' : 'visible',
              display: !hasCamera || cameraOff ? 'none' : 'block',
            }"
          />
        </div>
        <div
          ref="remoteVideoContainerRef"
          :class="['remote-video-container', { connected: streamState === 'open' }]"
        >
          <div v-if="streamState !== 'open'" class="session-status-overlay">
            <div class="session-status-card">
              <div class="session-status-title">{{ sessionStatusTitle }}</div>
              <div class="session-status-desc">{{ sessionStatusDescription }}</div>
              <button
                v-if="streamState === 'closed'"
                class="session-status-btn"
                @click="onStartChat"
              >
                重新开始
              </button>
            </div>
          </div>
          <div
            v-if="streamState === 'open' && showChatRecords && !isLandscape"
            :class="`chat-records-container inline`"
            :style="
              !hasCamera || cameraOff ? 'width:80%;padding-bottom:12px;' : 'padding-bottom:12px;'
            "
          >
            <ChatRecords
              ref="chatRecordsInstanceRef"
              :chat-records="chatRecords.filter((_, index) => index >= chatRecords.length - 4)"
            />
          </div>
        </div>

        <div v-if="toolsVisible" class="actions">
          <ActionGroup />
        </div>
      </div>
      <template v-if="inputVisible">
        <template v-if="(!hasMic || micMuted) && streamState === 'open'">
          <ChatInput
            :replying="replying"
            @interrupt="onInterrupt"
            @send="onSend"
            @stop="wsChatState.startSession"
          />
        </template>
        <template v-else-if="webcamAccessed">
          <ChatBtn
            :audio-source-callback="audioSourceCallback"
            :stream-state="streamState"
            wave-color="#7873F6"
            @start-chat="onStartChat"
          />
        </template>
      </template>
    </div>
    <div
      v-if="streamState === 'open' && showChatRecords && isLandscape"
      class="chat-records-container"
    >
      <ChatRecords ref="chatRecordsInstanceRef" :chat-records="chatRecords" />
    </div>
    <div v-if="appState.currentSessionId" class="session-id-pill">
      <span class="session-id-label">Session</span>
      <span class="session-id-value">{{ appState.currentSessionId }}</span>
    </div>
    <div v-if="reportChecked" class="report-btn-wrapper">
      <button class="report-btn" @click="showReport = true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
        查看面试报告
      </button>
    </div>
    <div v-else-if="reportPending" class="report-status-pill">正在生成报告...</div>
    <div v-else-if="reportFailed" class="report-status-pill failed">
      报告生成失败{{ reportError ? `：${reportError}` : '' }}
    </div>
    <ReportModal
      v-if="appState.currentSessionId"
      :visible="showReport"
      :session-id="appState.currentSessionId"
      @close="showReport = false"
    />
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { computed, nextTick, onMounted, ref, useTemplateRef, watch } from 'vue'

import ActionGroup from '@/components/ActionGroup.vue'
import ChatBtn from '@/components/ChatBtn.vue'
import ChatInput from '@/components/ChatInput.vue'
import ChatRecords from '@/components/ChatRecords.vue'
import ReportModal from '@/components/ReportModal.vue'
import { getInterviewSession } from '@/apis'
import { useAppStore } from '@/store/app'
import { useChatStore } from '@/store/chat'
import { useWSVideoChatStore } from '@/store/ws'
import { useMediaStore } from '@/store/media'
import { useVisionStore } from '@/store/vision'

const visionState = useVisionStore()
const wsChatState = useWSVideoChatStore()
const chatState = useChatStore()
const appState = useAppStore()
const mediaState = useMediaStore()
const wrapRef = ref<HTMLDivElement>()

const localVideoContainerRef = ref<HTMLDivElement>()
const remoteVideoContainerRef = ref<HTMLDivElement>()
const localVideoRef = ref<HTMLVideoElement>()

const audioSourceCallback = (): MediaStream | null => mediaState.localStream

// Report state
const showReport = ref(false)
const reportChecked = ref(false)
const reportPending = ref(false)
const reportFailed = ref(false)
const reportError = ref('')
const reportPollTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const sessionBootstrapPending = ref(false)
const { streamState } = storeToRefs(wsChatState)
const { replying, showChatRecords } = storeToRefs(chatState)
const { chatRecords, inputVisible, toolsVisible } = storeToRefs(appState)
const { hasCamera, hasMic, micMuted, cameraOff, webcamAccessed } = storeToRefs(mediaState)
const { wrapperRect, isLandscape } = storeToRefs(visionState)
const sessionStatusTitle = computed(() => {
  if (streamState.value === 'waiting') return '正在启动面试'
  if (!webcamAccessed.value) return '正在申请设备权限'
  return '面试尚未开始'
})
const sessionStatusDescription = computed(() => {
  if (streamState.value === 'waiting') return '正在连接数字人与语音链路，请稍等几秒。'
  if (!webcamAccessed.value) return '请允许访问摄像头和麦克风，系统随后会自动开始面试。'
  return '如果长时间没有进入对话，可以点击下方按钮重试。'
})

async function ensureSessionStarted(force = false) {
  if (!appState.currentSessionId) return
  if (streamState.value === 'open' || streamState.value === 'waiting') return
  if (sessionBootstrapPending.value && !force) return
  sessionBootstrapPending.value = true
  try {
    await wsChatState.startSession()
  } finally {
    sessionBootstrapPending.value = false
  }
}

async function checkReportReady() {
  const sid = appState.currentSessionId
  if (!sid) return
  try {
    const resp = await getInterviewSession(sid)
    if (resp.ok) {
      const data = await resp.json()
      reportPending.value = ['pending', 'running'].includes(data.report_status)
      reportFailed.value = data.report_status === 'failed'
      reportError.value = data.report_error || ''
      if (data.report_status === 'ready' || data.report_ready) {
        reportChecked.value = true
        reportPending.value = false
        if (reportPollTimer.value) clearTimeout(reportPollTimer.value)
        return
      }
      if (data.report_status === 'failed') {
        if (reportPollTimer.value) clearTimeout(reportPollTimer.value)
        return
      }
    }
  } catch {}
  if (reportPollTimer.value) clearTimeout(reportPollTimer.value)
  reportPollTimer.value = setTimeout(checkReportReady, 2000)
}

watch(
  () => appState.currentSessionId,
  (sessionId) => {
    reportChecked.value = false
    reportPending.value = false
    reportFailed.value = false
    reportError.value = ''
    if (reportPollTimer.value) clearTimeout(reportPollTimer.value)
    if (sessionId) {
      void checkReportReady()
    }
  },
)

watch(replying, (v) => {
  if (!v && appState.currentSessionId && !reportChecked.value) {
    checkReportReady()
  }
})

onMounted(() => {
  const wrapperRef = wrapRef.value
  visionState.wrapperRef = wrapperRef
  wrapperRef!.getBoundingClientRect()
  wrapperRect.value.width = wrapperRef!.clientWidth
  wrapperRect.value.height = wrapperRef!.clientHeight
  visionState.isLandscape = wrapperRect.value.width > wrapperRect.value.height

  visionState.remoteVideoContainerRef = remoteVideoContainerRef.value
  visionState.localVideoContainerRef = localVideoContainerRef.value
  visionState.localVideoRef = localVideoRef.value
  visionState.wrapperRef = wrapRef.value

  nextTick(() => {
    void ensureSessionStarted()
  })
})

watch(
  [() => appState.currentSessionId, webcamAccessed, streamState],
  ([sessionId, accessed, state]) => {
    if (!sessionId) return
    if (state === 'open' || state === 'waiting') return
    if (accessed || state === 'closed') {
      void ensureSessionStarted()
    }
  }
)

function onStartChat(): void {
  void ensureSessionStarted(true)
}

function onInterrupt(): void {
  wsChatState.interrupt()
}

const chatRecordsInstanceRef =
  useTemplateRef<InstanceType<typeof ChatRecords>>('chatRecordsInstanceRef')
function onSend(message: string): void {
  if (!message) return
  wsChatState.sendText(message)
  chatRecordsInstanceRef.value?.scrollToBottom()
}
</script>
<style lang="less" scoped>
@import '../VideoChat/index.less';

.session-status-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 2;
}

.session-status-card {
  width: min(360px, 100%);
  padding: 24px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(14px);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
  text-align: center;
}

.session-status-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}

.session-status-desc {
  margin-top: 10px;
  font-size: 14px;
  line-height: 1.6;
  color: #64748b;
}

.session-status-btn {
  margin-top: 18px;
  height: 40px;
  padding: 0 18px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.session-id-pill {
  position: fixed;
  top: 18px;
  right: 24px;
  z-index: 100;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: min(70vw, 560px);
  min-height: 38px;
  padding: 0 14px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.86);
  color: #fff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);
}

.session-id-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.72);
}

.session-id-value {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 900px) {
  .session-id-pill {
    top: 14px;
    right: 14px;
    max-width: calc(100vw - 28px);
  }
}
</style>
