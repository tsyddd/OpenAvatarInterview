<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    message: string
    role: string
    style?: string
  }>(),
  {}
)
</script>

<template>
  <div :class="['answer-message-container', role]" :style="style">
    <div class="answer-message-text">
      {{ message }}
    </div>
  </div>
</template>

<style scoped lang="less">
.answer-message-container {
  padding: 8px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;

  &.human {
    background: rgba(255, 255, 255, 0.75);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.6);
    color: #334155;
    margin-right: 0;
  }

  &.avatar {
    background: linear-gradient(135deg, #7c3aed, #6d28d9);
    color: #ffffff;
    box-shadow: 0 2px 8px rgba(124, 58, 237, 0.2);
  }
}
</style>
