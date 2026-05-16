<script setup lang="ts">
import Iconfont, { Send, HandStop } from '@/components/Iconfont'
import { insertStringAt } from '@/utils/utils'
import { useTemplateRef } from 'vue'

const props = withDefaults(
  defineProps<{
    replying: boolean
  }>(),
  {}
)
const emit = defineEmits(['send', 'stop', 'interrupt'])

let inputHeight = 24
let rowsDivRef = useTemplateRef<HTMLDivElement>('rowsDivRef')
let chatInputRef = useTemplateRef<HTMLInputElement>('chatInputRef')
let inputValue = ''
function on_chat_input_keydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    if (event.altKey) {
      if (chatInputRef.value) {
        chatInputRef.value.value = insertStringAt(
          chatInputRef.value.value,
          '\n',
          chatInputRef.value.selectionStart || 0
        )
        chatInputRef.value.dispatchEvent(new InputEvent('input'))
      }
    } else {
      event.preventDefault()
      on_send()
    }
  }
}
async function on_send() {
  if (chatInputRef.value) {
    emit('send', chatInputRef.value.value)
    chatInputRef.value.value = ''
  }
}
function on_chat_input(event: Event) {
  if (rowsDivRef.value) {
    rowsDivRef.value.textContent = (event.target as any).value.replace(/\n$/, '\n\n')
    inputHeight = rowsDivRef.value.offsetHeight
  }
}

function onStop() {
  emit('stop')
}
function onInterrupt() {
  emit('interrupt')
}
</script>

<template>
  <div class="chat-input-container">
    <div class="stop-chat-btn" @click="onStop" />

    <div class="chat-input-inner">
      <div class="chat-input-wrapper">
        <textarea
          ref="chatInputRef"
          class="chat-input"
          placeholder="输入消息..."
          :style="`height:${inputHeight}px`"
          @keydown="on_chat_input_keydown"
          @input="on_chat_input"
        />
        <div ref="rowsDivRef" class="rowsDiv">
          {{ inputValue }}
        </div>
      </div>
      <template v-if="replying">
        <button class="interrupt-btn" @click="onInterrupt">
          <Iconfont :icon="HandStop" :color="'#fff'" />
        </button>
      </template>
      <template v-else>
        <button class="send-btn" @click="on_send">
          <Iconfont :icon="Send" :color="'#fff'" />
        </button>
      </template>
    </div>
  </div>
</template>

<style scoped lang="less">
.chat-input-container {
  height: 15%;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 84px;
  width: calc(100% - 140px);
  margin: auto;

  .chat-input-inner {
    padding: 0 12px;
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(16px);
    height: 56px;
    flex: 1;
    display: flex;
    align-items: center;
    border: 1px solid rgba(255, 255, 255, 0.9);
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(124, 58, 237, 0.06), 0 1px 4px rgba(0, 0, 0, 0.04);

    .chat-input-wrapper {
      flex: 1;
      position: relative;
      display: flex;
      align-items: center;

      .chat-input {
        width: 100%;
        border: none;
        outline: none;
        color: #1e293b;
        font-size: 15px;
        font-weight: 400;
        resize: none;
        padding: 0;
        margin: 8px 0;
        line-height: 24px;
        max-height: 48px;
        min-height: 24px;
        background: transparent;
        font-family: inherit;

        &::placeholder {
          color: #94a3b8;
        }
      }

      .rowsDiv {
        position: absolute;
        left: 0;
        right: 0;
        z-index: -1;
        visibility: hidden;
        font-size: 15px;
        font-weight: 400;
        line-height: 24px;
        white-space: pre-wrap;
        word-wrap: break-word;
      }
    }

    .send-btn,
    .interrupt-btn {
      border: none;
      flex: 0 0 auto;
      background: linear-gradient(135deg, #7c3aed, #6d28d9);
      border-radius: 12px;
      height: 32px;
      width: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-left: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
      box-shadow: 0 2px 8px rgba(124, 58, 237, 0.25);

      &:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.35);
      }
    }

    .interrupt-btn {
      background: linear-gradient(135deg, #ef4444, #dc2626);
      box-shadow: 0 2px 8px rgba(239, 68, 68, 0.25);

      &:hover {
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.35);
      }
    }
  }

  .stop-chat-btn {
    cursor: pointer;
    margin-right: 12px;
    height: 32px;
    width: 32px;
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: 12px;
    background: linear-gradient(135deg, #7c3aed, #6d28d9);
    box-shadow: 0 2px 8px rgba(124, 58, 237, 0.25);
    transition: all 0.2s ease;

    &:hover {
      transform: scale(1.05);
      box-shadow: 0 4px 12px rgba(124, 58, 237, 0.35);
    }

    &::after {
      content: ' ';
      width: 12px;
      height: 12px;
      border-radius: 3px;
      background: #ffffff;
    }
  }
}
</style>
