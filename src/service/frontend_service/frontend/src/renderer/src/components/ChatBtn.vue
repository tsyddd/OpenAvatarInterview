<template>
  <div class="player-controls">
    <div
      :class="[
        'chat-btn',
        streamState === StreamState.closed && 'start-chat',
        streamState === StreamState.open && 'stop-chat',
      ]"
      @click="onStartChat"
    >
      <template v-if="streamState === StreamState.closed">
        <span>点击开始对话</span>
      </template>
      <template v-else-if="streamState === StreamState.waiting">
        <div class="waiting-icon-text">
          <div class="icon" title="spinner">
            <Spin wrapper-class-name="spin-icon" />
          </div>
          <span>等待中</span>
        </div>
      </template>
      <template v-else>
        <div class="stop-chat-inner" />
      </template>
    </div>
    <template v-if="streamState === StreamState.open">
      <div class="input-audio-wave">
        <AudioWave
          :audio-source-callback="audioSourceCallback"
          :stream-state="streamState"
          :wave-color="waveColor"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Spin } from 'ant-design-vue'
import { StreamState } from '@/interface/voiceChat'
import AudioWave from '@/components/AudioWave.vue'

const props = withDefaults(
  defineProps<{
    streamState: StreamState
    onStartChat: any
    audioSourceCallback: () => MediaStream | null
    waveColor: string
  }>(),
  {
    streamState: StreamState.closed,
  }
)

const emit = defineEmits([])
</script>

<style scoped lang="less">
.player-controls {
  height: 15%;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 84px;

  .chat-btn {
    height: 56px;
    width: 280px;
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: 999px;
    background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 50%, #5b21b6 100%);
    box-shadow: 0 4px 16px rgba(124, 58, 237, 0.3), 0 2px 4px rgba(0, 0, 0, 0.1);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 2;
    cursor: pointer;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(124, 58, 237, 0.4), 0 4px 8px rgba(0, 0, 0, 0.12);
    }

    &:active {
      transform: translateY(0);
      box-shadow: 0 2px 8px rgba(124, 58, 237, 0.3);
    }
  }

  .start-chat {
    font-size: 16px;
    font-weight: 600;
    text-align: center;
    color: #ffffff;
    letter-spacing: 0.5px;
  }

  .waiting-icon-text {
    width: 80px;
    align-items: center;
    font-size: 16px;
    font-weight: 500;
    color: #ffffff;
    margin: 0 var(--spacing-sm);
    display: flex;
    justify-content: space-evenly;
    gap: var(--size-1);

    .icon {
      width: 25px;
      height: 25px;
      fill: #ffffff;
      stroke: #ffffff;
      color: #ffffff;
    }
    .spin-icon {
      color: #fff;
    }
    :global(.ant-spin-dot-item) {
      background-color: #fff !important;
    }
  }

  .stop-chat {
    width: 56px;
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    box-shadow: 0 4px 16px rgba(239, 68, 68, 0.3);

    &:hover {
      box-shadow: 0 8px 24px rgba(239, 68, 68, 0.4);
    }

    .stop-chat-inner {
      width: 22px;
      height: 22px;
      border-radius: 6px;
      background: #ffffff;
    }
  }

  .input-audio-wave {
    position: absolute;
  }
}
</style>
