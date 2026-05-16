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
          <video
            v-if="!avatarType"
            v-show="streamState === 'open'"
            ref="remoteVideoRef"
            class="remote-video"
            autoplay
            playsinline
            :muted="volumeMuted"
            @playing="onplayingRemoteVideo"
          />
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
            @stop="videoChatState.startWebRTC"
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
import { onMounted, ref, useTemplateRef, watch } from 'vue'

import ActionGroup from '@/components/ActionGroup.vue'
import ChatBtn from '@/components/ChatBtn.vue'
import ChatInput from '@/components/ChatInput.vue'
import ChatRecords from '@/components/ChatRecords.vue'
import ReportModal from '@/components/ReportModal.vue'
import { getInterviewAnalysis } from '@/apis'
import { useAppStore } from '@/store/app'
import { useChatStore } from '@/store/chat'
import { useVideoChatStore } from '@/store/webrtc'
import { useMediaStore } from '@/store/media'
import { useVisionStore } from '@/store/vision'

const visionState = useVisionStore()
const videoChatState = useVideoChatStore()
const chatState = useChatStore()
const appState = useAppStore()
const mediaState = useMediaStore()
const wrapRef = ref<HTMLDivElement>()

const localVideoContainerRef = ref<HTMLDivElement>()
const remoteVideoContainerRef = ref<HTMLDivElement>()
const localVideoRef = ref<HTMLVideoElement>()
const remoteVideoRef = ref<HTMLVideoElement>()
const remoteAspectRatio = ref('9 / 16')
const onplayingRemoteVideo = (): void => {
  if (remoteVideoRef.value) {
    remoteAspectRatio.value = `${remoteVideoRef.value.videoWidth} / ${remoteVideoRef.value.videoHeight}`
  }
}

const audioSourceCallback = (): MediaStream | null => mediaState.localStream

// Report state
const showReport = ref(false)
const reportChecked = ref(false)
const reportPollTimer = ref<ReturnType<typeof setTimeout> | null>(null)
let reportCheckCount = 0
const { streamState } = storeToRefs(videoChatState)
const { volumeMuted, replying, showChatRecords } = storeToRefs(chatState)
const { avatarType, chatRecords, inputVisible, toolsVisible } = storeToRefs(appState)
const { hasCamera, hasMic, micMuted, cameraOff, webcamAccessed } = storeToRefs(mediaState)
const { wrapperRect, isLandscape } = storeToRefs(visionState)

async function checkReportReady() {
  const sid = appState.currentSessionId
  if (!sid || reportChecked.value) return
  try {
    const resp = await getInterviewAnalysis(sid)
    if (resp.ok) {
      const data = await resp.json()
      if (data.final_evaluation) {
        reportChecked.value = true
        if (reportPollTimer.value) clearTimeout(reportPollTimer.value)
        return
      }
    }
  } catch {}
  reportCheckCount++
  if (reportCheckCount < 30) {
    reportPollTimer.value = setTimeout(checkReportReady, 2000)
  }
}

watch(replying, (v) => {
  if (!v && appState.currentSessionId && !reportChecked.value) {
    reportCheckCount = 0
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
  visionState.remoteVideoRef = remoteVideoRef.value
  visionState.wrapperRef = wrapRef.value
})

function onStartChat(): void {
  videoChatState.startWebRTC()
}

function onInterrupt(): void {
  videoChatState.interrupt()
}

const chatRecordsInstanceRef =
  useTemplateRef<InstanceType<typeof ChatRecords>>('chatRecordsInstanceRef')
function onSend(message: string): void {
  if (!message) return
  videoChatState.sendText(message)
  chatRecordsInstanceRef.value?.scrollToBottom()
}
</script>
<style lang="less" scoped>
@import './index.less';
</style>
