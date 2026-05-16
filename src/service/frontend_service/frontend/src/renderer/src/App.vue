<script setup lang="ts">
import { ConfigProvider } from 'ant-design-vue'
import { storeToRefs } from 'pinia'

import HomeView from '@/views/HomeView/index.vue'
import WebcamPermission from '@/components/WebcamPermission.vue'
import { antdLocale, locale } from '@/langs'
import VideoChat from '@/views/VideoChat/index.vue'
import WSVideoChat from './views/WSVideoChat/index.vue'
import { useAppStore } from './store/app'
import { useMediaStore } from './store/media'
import isElectron from './utils/isElectron'

const appState = useAppStore()
const mediaState = useMediaStore()
const { chatMode, appMode } = storeToRefs(appState)
appState.init()
</script>
<template>
  <ConfigProvider :locale="antdLocale[locale]">
    <HomeView v-if="appMode === 'home'" />
    <template v-else>
      <div
        v-if="isElectron"
        class="wrap"
        :style="{
          backgroundImage: 'none',
        }"
      >
        <WebcamPermission v-if="!mediaState.webcamAccessed" auto-access />
        <template v-if="chatMode === 'ws'">
          <WSVideoChat />
        </template>
        <template v-else>
          <VideoChat />
        </template>
      </div>
      <div v-else class="wrap">
        <WebcamPermission v-if="!mediaState.webcamAccessed" />
        <template v-if="chatMode === 'ws'">
          <WSVideoChat />
        </template>
        <template v-else>
          <VideoChat />
        </template>
      </div>
    </template>
  </ConfigProvider>
</template>
<style lang="less" scoped>
.wrap {
  height: calc(max(80vh, 100%));
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 30%, #e0e7ff 60%, #dbeafe 100%);
  position: relative;
  overflow: hidden;
  *::-webkit-scrollbar {
    display: none;
  }
}
</style>
