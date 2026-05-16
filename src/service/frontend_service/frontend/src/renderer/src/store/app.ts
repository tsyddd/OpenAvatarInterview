import { message } from 'ant-design-vue'
import { defineStore } from 'pinia'

import { initConfig, makeURL } from '@/apis'
import { useMediaStore } from './media'
import { TextPayload } from '@renderer/interface/eventType'

type ChatRecord = {
  id: string
  role: 'human' | 'avatar'
  message: string
  cancelled?: boolean
  invalid?: boolean
} & TextPayload

interface ResumeItem {
  id: string
  filename: string
  uploadDate: string
  questions: any[]
}

const APP_STORAGE_KEY = 'open-avatar-interview-app-state'

interface AppState {
  avatarType: '' | 'lam'
  avatarWSRoute: string
  wsSessionRoute: string
  avatarAssetsPath: string
  rtcConfig: RTCConfiguration | undefined
  chatMode: 'webrtc' | 'ws'
  chatRecords: ChatRecord[]

  toolsVisible: boolean
  inputVisible: boolean

  appMode: 'home' | 'interview'
  resumeList: ResumeItem[]
  selectedResumeId: string | null
  currentSessionId: string | null
}

export const useAppStore = defineStore('appStore', {
  state: (): AppState => ({
    avatarType: '',
    avatarWSRoute: '',
    wsSessionRoute: '',
    avatarAssetsPath: '',
    rtcConfig: undefined,
    chatMode: 'webrtc',
    chatRecords: [],
    toolsVisible: true,
    inputVisible: true,
    appMode: 'home',
    resumeList: [],
    selectedResumeId: null,
    currentSessionId: null,
  }),
  actions: {
    _persistState() {
      if (typeof window === 'undefined') return
      localStorage.setItem(
        APP_STORAGE_KEY,
        JSON.stringify({
          resumeList: this.resumeList,
          selectedResumeId: this.selectedResumeId,
          currentSessionId: this.currentSessionId,
        })
      )
    },
    _restoreState() {
      if (typeof window === 'undefined') return
      const raw = localStorage.getItem(APP_STORAGE_KEY)
      if (!raw) return
      try {
        const parsed = JSON.parse(raw) as Partial<{
          resumeList: ResumeItem[]
          selectedResumeId: string | null
          currentSessionId: string | null
        }>
        this.resumeList = Array.isArray(parsed.resumeList) ? parsed.resumeList : []
        this.selectedResumeId = parsed.selectedResumeId || (this.resumeList[0]?.id ?? null)
        this.currentSessionId = parsed.currentSessionId || null
      } catch {
        localStorage.removeItem(APP_STORAGE_KEY)
      }
    },
    async init() {
      const mediaStore = useMediaStore()
      this._restoreState()
      return initConfig()
        .then((res) => res.json())
        .then((config) => {
          if (config.detail) {
            message.error(config.detail)
            return
          }
          if (config.rtc_configuration) {
            this.rtcConfig = config.rtc_configuration
          }
          if (config.chat_mode) {
            this.chatMode = config.chat_mode === 'ws' ? 'ws' : 'webrtc'
          }
          config.avatar_config = config.avatar_config || {}
          if (config.avatar_config) {
            this.avatarType = config.avatar_config.avatar_type || ''
            this.avatarWSRoute = config.avatar_config.avatar_ws_route || ''
            this.avatarAssetsPath = config.avatar_config.avatar_assets_path
              ? makeURL(config.avatar_config.avatar_assets_path)
              : ''
            if (config.avatar_config.ws_session_route) {
              this.wsSessionRoute = config.avatar_config.ws_session_route
              if (!this.avatarWSRoute) {
                this.avatarWSRoute = config.avatar_config.ws_session_route
              }
            }
          }
          if (config.ws_session_route) {
            this.wsSessionRoute = config.ws_session_route
            if (!this.avatarWSRoute) {
              this.avatarWSRoute = config.ws_session_route
            }
          }
          if (config.track_constraints) {
            mediaStore.setTrackConstraints(config.track_constraints)
          }
        })
        .catch((e) => {
          message.error(
            `服务端链接失败，请检查是否能正确访问到 OpenAvatarChat 服务端: ${e instanceof Error ? e.message : String(e)}`
          )
        })
    },
    resetChatRecords() {
      this.chatRecords = []
    },
    startInterview(sessionId?: string) {
      this.currentSessionId = sessionId || null
      this.appMode = 'interview'
      this._persistState()
    },
    goHome() {
      this.currentSessionId = null
      this.appMode = 'home'
      this._persistState()
    },
    addResume(resume: ResumeItem) {
      this.resumeList = [...this.resumeList, resume]
      this.selectedResumeId = resume.id
      this._persistState()
    },
    selectResume(id: string) {
      this.selectedResumeId = id
      this._persistState()
    },
    removeResume(id: string) {
      this.resumeList = this.resumeList.filter((r) => r.id !== id)
      if (this.selectedResumeId === id) {
        this.selectedResumeId = this.resumeList.length > 0 ? this.resumeList[0].id : null
      }
      if (this.currentSessionId === id) {
        this.currentSessionId = null
      }
      this._persistState()
    },
  },
})
