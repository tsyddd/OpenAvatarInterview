<template>
  <div class="action-group">
    <div v-if="hasCamera">
      <div v-click-outside="() => (cameraListShow = false)" class="action" @click="handleCameraOff">
        <Iconfont :icon="cameraOff ? CameraOff : CameraOn" />
        <div
          v-if="streamState === 'closed'"
          class="corner"
          @click.stop.prevent="() => (cameraListShow = !cameraListShow)"
        >
          <div class="corner-inner" />
        </div>
        <div
          v-show="cameraListShow && streamState === 'closed'"
          class="selectors"
          :class="{ left: isLandscape }"
        >
          <div
            v-for="device in availableVideoDevices"
            :key="device.deviceId"
            class="selector"
            @click.stop="
              () => {
                handleDeviceChange(device.deviceId)
                cameraListShow = false
              }
            "
          >
            {{ device.label }}
            <div
              v-if="selectedVideoDevice && device.deviceId === selectedVideoDevice.deviceId"
              class="active-icon"
            >
              <CheckIcon />
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="hasMic">
      <div v-click-outside="() => (micListShow = false)" class="action" @click="handleMicMuted">
        <Iconfont :icon="micMuted ? MicOff : MicOn" />
        <div
          v-if="streamState === 'closed'"
          class="corner"
          @click.stop.prevent="() => (micListShow = !micListShow)"
        >
          <div class="corner-inner" />
        </div>
        <div
          v-show="micListShow && streamState === 'closed'"
          class="selectors"
          :class="{ left: isLandscape }"
        >
          <div
            v-for="device in availableAudioDevices"
            :key="device.deviceId"
            class="selector"
            @click.stop="
              (e) => {
                handleDeviceChange(device.deviceId)
                micListShow = false
              }
            "
          >
            {{ device.label }}
            <div
              v-if="selectedAudioDevice && device.deviceId === selectedAudioDevice.deviceId"
              class="active-icon"
            >
              <CheckIcon />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="action" @click="handleVolumeMute">
      <Iconfont :icon="volumeMuted ? VolumeOff : VolumeOn" />
    </div>
    <div v-if="wrapperRect.width > 300">
      <div class="action" @click="handleSubtitleToggle">
        <Iconfont :icon="showChatRecords ? SubtitleOn : SubtitleOff" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'

import { useMediaStore } from '@/store/media'
import { useChatStore } from '@/store/chat'
import { useVideoChatStore } from '@/store/webrtc'
import { useWSVideoChatStore } from '@/store/ws'
import { useAppStore } from '@/store/app'
import { useVisionStore } from '@/store/vision'
import Iconfont, {
  CameraOff,
  CameraOn,
  CheckIcon,
  MicOff,
  MicOn,
  SubtitleOff,
  SubtitleOn,
  VolumeOff,
  VolumeOn,
} from './Iconfont'

const chatStore = useChatStore()
const mediaStore = useMediaStore()
const visionStore = useVisionStore()
const appStore = useAppStore()
const videoChatStore = useVideoChatStore()
const wsChatStore = useWSVideoChatStore()

const {
  hasCamera,
  hasMic,
  cameraOff,
  micMuted,
  selectedAudioDevice,
  selectedVideoDevice,
  availableAudioDevices,
  availableVideoDevices,
} = storeToRefs(mediaStore)

const { volumeMuted, showChatRecords } = storeToRefs(chatStore)
const streamState = computed(() =>
  appStore.chatMode === 'ws' ? wsChatStore.streamState : videoChatStore.streamState
)

const { handleVolumeMute, handleSubtitleToggle } = chatStore
const { handleCameraOff, handleMicMuted, handleDeviceChange } = mediaStore

const { wrapperRect, isLandscape } = storeToRefs(visionStore)
const micListShow = ref(false)
const cameraListShow = ref(false)
</script>

<style lang="less" scoped>
.action-group {
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.6);
  padding: 4px;
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);

  .action {
    cursor: pointer;
    width: 40px;
    height: 40px;
    border-radius: 12px;
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    color: #475569;
    transition: all 0.2s ease;

    .corner {
      position: absolute;
      right: 0px;
      bottom: 0px;
      padding: 3px;

      .corner-inner {
        width: 6px;
        height: 6px;
        border-top: 3px transparent solid;
        border-left: 3px transparent solid;
        border-bottom: 3px #94a3b8 solid;
        border-right: 3px #94a3b8 solid;
      }
    }

    .selectors {
      position: absolute;
      top: 0;
      left: calc(100%);
      margin-left: 6px;
      max-height: 150px;

      &.left {
        left: 0;
        margin-left: -6px;
        transform: translateX(-100%);
      }

      border-radius: 14px;
      width: max-content;
      overflow: hidden;
      overflow: auto;

      background: rgba(255, 255, 255, 0.9);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.8);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);

      .selector {
        max-width: 250px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        position: relative;
        cursor: pointer;
        height: 40px;
        line-height: 40px;
        color: #334155;
        font-size: 13px;
        transition: background 0.15s ease;

        &:hover {
          background: rgba(124, 58, 237, 0.08);
        }

        padding-left: 14px;
        padding-right: 44px;

        .active-icon {
          position: absolute;
          right: 10px;
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          top: 0;
          color: #7c3aed;
        }
      }
    }
  }

  .action:hover {
    background: rgba(124, 58, 237, 0.1);
    color: #7c3aed;
  }
}

.action-group + .action-group {
  margin-top: 8px;
}
</style>
