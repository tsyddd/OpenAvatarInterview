<script setup lang="ts">
import { useMediaStore } from '@/store/media'
import { VideoCameraOutlined } from '@ant-design/icons-vue'
import { onMounted } from 'vue'

const props = withDefaults(
  defineProps<{
    autoAccess?: boolean
  }>(),
  {
    autoAccess: false,
  }
)
const mediaState = useMediaStore()
const accessClick = async (): Promise<void> => {
  mediaState.accessDevice()
}
onMounted(() => {
  if (props.autoAccess) {
    accessClick()
  }
})

const text = '点击允许访问摄像头和麦克风'
</script>

<template>
  <div v-show="!autoAccess" class="access-wrap" @click="accessClick">
    <div class="access-card">
      <span class="icon-wrap">
        <VideoCameraOutlined />
      </span>
      <span class="access-text">{{ text }}</span>
    </div>
  </div>
</template>
<style lang="less" scoped>
.access-wrap {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(12px);
  z-index: 100;
}

.access-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 40px 48px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 24px;
  box-shadow: 0 8px 32px rgba(124, 58, 237, 0.1), 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(124, 58, 237, 0.15), 0 4px 12px rgba(0, 0, 0, 0.06);
  }
}

.icon-wrap {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: #7c3aed;
  background: linear-gradient(135deg, #f5f3ff, #ede9fe);
  border-radius: 16px;
}

.access-text {
  font-size: 15px;
  font-weight: 500;
  color: #475569;
}
</style>
