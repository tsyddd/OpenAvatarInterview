<script setup lang="ts">
import { nextTick, useTemplateRef, watch } from 'vue'
import ChatMessage from '@/components/ChatMessage.vue'

interface ChatRecordItem {
  id: string
  role: 'human' | 'avatar'
  message: string
  stream_key?: string
  cancelled?: boolean
  invalid?: boolean
}

const props = defineProps<{
  chatRecords: ChatRecordItem[]
}>()

let containerRef = useTemplateRef<HTMLElement>('containerRef')

watch(
  () => props.chatRecords,
  () => {
    if (props.chatRecords) {
      nextTick().then(() => {
        scrollToBottom()
      })
    }
  }
)
function scrollToBottom(): void {
  if (containerRef.value) {
    containerRef.value.scrollTop = containerRef.value.scrollHeight
  }
}

defineExpose({
  scrollToBottom,
})
</script>

<template>
  <div ref="containerRef" class="chat-records">
    <div class="chat-records-inner">
      <template v-for="item in chatRecords" :key="item.id">
        <div
          v-show="item.message && !(item.cancelled && item.invalid)"
          :class="['chat-message', item.role, { cancelled: item.cancelled }]"
        >
          <ChatMessage
            :message="item.message"
            :role="item.role"
            :style="item.cancelled ? 'background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;box-shadow:0 2px 8px rgba(245,158,11,0.25);' : ''"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<style lang="less">
.chat-records {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  padding: 4px;

  &::-webkit-scrollbar {
    width: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 3px;
  }
}

.chat-records-inner {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: end;
  width: 100%;
  height: auto;
  min-height: 100%;

  .chat-message {
    margin-bottom: 10px;
    max-width: 80%;

    &.human {
      align-self: flex-end;
    }

    &.avatar {
      align-self: flex-start;
    }

    &.cancelled {
      opacity: 0.95;
    }

    &:last-child {
      margin-bottom: 0;
    }

    .stream-key {
      margin-bottom: 4px;
      font-size: 11px;
      color: #94a3b8;
      word-break: break-all;
    }
  }
}
</style>
