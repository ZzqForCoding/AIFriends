<script setup lang="ts">
/**
 * ChatField: 聊天弹窗主容器
 *
 * 2026-04 重构说明：
 *   1. 所有会话状态（friend/sessions/history/currentSessionId）迁移到 Pinia useChatStore，
 *      本组件只负责 UI 布局、DOM ref 管理和事件转发。
 *   2. 核心交互逻辑（懒创建、切换会话、删除会话、历史加载）全部下沉到 store，
 *      但本组件作为 ChatHistory / InputField 的父组件，需要协调两者的生命周期：
 *        - 切换 Session 后，先等 store 改状态 -> nextTick -> 再调 ChatHistory.resetAndLoad()
 *        - 懒创建 Session 后，同样需要 nextTick -> resetAndLoad()，否则 ChatHistory 拿不到新 sessionId
 *   3. 智能滚底逻辑保留在本层：收到新消息 / AI 流式增量时，只调 smartScrollToBottom()，
 *      由 ChatHistory 自行判断用户是否在底部，避免打断用户查看历史。
 */
import { computed, nextTick, ref, useTemplateRef } from 'vue';
import InputField from './input_field/InputField.vue';
import ChatHistory from './chat_history/ChatHistory.vue';
import { useChatStore } from '@/stores/chat';
import { useAudioStore } from '@/stores/audio';
import ChatSessions from './chat_sessions/ChatSessions.vue';

const chatStore = useChatStore()
const audioStore = useAudioStore()

const inputRef = useTemplateRef('input-ref')
const chatHistoryRef = useTemplateRef('chat-history-ref')

// 侧边栏展开状态保留在组件层，因为只影响本组件内部布局
const isSidebarOpen = ref(true)

const modalStyle = computed(() => {
  if (chatStore.characterBackground) {
    return {
      backgroundImage: `url(${chatStore.characterBackground})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat',
    }
  } else {
    return {}
  }
})

/**
 * 切换会话并加载历史
 * 关键：必须先 await chatStore.switchSession()，再 await nextTick()，
 * 保证 ChatHistory 的 props.sessionId 已更新为新的 sessionId，然后再 resetAndLoad()。
 */
async function switchAndLoadSession(sessionId: number) {
  await chatStore.switchSession(sessionId)
  await nextTick()
  chatHistoryRef.value?.resetAndLoad()
  inputRef.value?.focus()
}

/**
 * 新建真实会话（用户点击侧边栏 +）
 * 先中断当前可能正在进行的流式输出和音频，再创建 Session，创建成功后加载历史。
 */
async function handleCreateSession() {
  inputRef.value?.abortChat()
  audioStore.stop()
  await chatStore.createSession()
  await nextTick()
  chatHistoryRef.value?.resetAndLoad()
  inputRef.value?.focus()
}

/**
 * 懒创建 Session 完成后的回调（由 InputField 在虚拟新对话下发送第一条消息时触发）
 * 此时 session 已创建，需要清空前端虚拟开场白，并从后端加载真实历史（含开场白）。
 */
async function handleSessionCreated(session: any) {
  chatStore.handleSessionCreated(session)
  await nextTick()
  chatHistoryRef.value?.resetAndLoad()
}

/**
 * 删除会话后的 UI 协调
 * 如果删的是当前会话，store 会自动切到下一个；切完后需要再加载新当前会话的历史。
 */
async function handleDeleteSession(sessionId: number) {
  const wasCurrent = sessionId === chatStore.currentSessionId
  await chatStore.deleteSession(sessionId)
  if (wasCurrent && chatStore.currentSessionId) {
    await nextTick()
    chatHistoryRef.value?.resetAndLoad()
  }
}

/**
 * 打开弹窗
 * 虚拟新对话：showModal 会自行插入前端开场白，不需要请求历史。
 * 真实会话：需要显式调用 resetAndLoad() 从后端加载历史消息。
 */
async function showModal() {
  chatStore.showModal()
  await nextTick()
  if (chatStore.currentSessionId) {
    chatHistoryRef.value?.resetAndLoad()
  }
  inputRef.value?.focus()
}

function handleClose() {
  chatStore.closeModal()
  inputRef.value?.close()
}

// ==================== 消息事件转发 ====================

/** 用户发送新消息：先入 history，再智能滚底 */
function handlePushBackMessage(msg: any) {
  chatStore.handlePushBackMessage(msg)
  chatHistoryRef.value?.smartScrollToBottom()
}

/** AI 流式回复增量：追加内容并智能滚底 */
function handleAddToLastMessage(delta: string) {
  chatStore.handleAddToLastMessage(delta)
  chatHistoryRef.value?.smartScrollToBottom()
}

// 开场白语音
// watch(() => chatStore.history, (val) => {
//   if (chatStore.hasPlayedOpening) return
//   if (
//     val.length === 2 &&
//     val[0].role === 'user' && val[0].content === '' &&
//     val[1].role === 'ai'
//   ) {
//     chatStore.hasPlayedOpening = true
//     const text = val[1].content
//     api.post('/api/friend/message/tts/tts/', { text })
//       .then(res => {
//         if (res.data.result === 'success' && res.data.audio) {
//           chatStore.stopOpeningAudio()
//           chatStore.openingAudio = new Audio('data:audio/mp3;base64,' + res.data.audio)
//           chatStore.openingAudio.onended = () => {
//             chatStore.openingAudio = null
//           }
//           return chatStore.openingAudio.play()
//         }
//       })
//       .catch(e => console.error('开场白语音播放失败', e))
//   }
// }, { deep: true })

defineExpose({
  showModal
})
</script>

<template>
  <div v-if="chatStore.isOpen" class="fixed inset-0 z-50 flex bg-base-100">
    <!-- ==================== 左侧 Sidebar ==================== -->
    <aside
      class="bg-base-200 border-r border-base-300 flex flex-col transition-all duration-300 shrink-0"
      :class="isSidebarOpen ? 'w-64' : 'w-0 overflow-hidden'"
    >
      <ChatSessions
        @close-sidebar="isSidebarOpen = false"
        @create-session="handleCreateSession"
        @switch-session="switchAndLoadSession"
        @delete-session="handleDeleteSession"
      />
    </aside>

    <!-- ==================== 右侧主区域 ==================== -->
    <main class="flex-1 flex flex-col min-w-0">
      <!-- Header -->
      <header class="h-16 flex items-center px-4 border-b border-base-300 shrink-0 gap-3 bg-base-100/80 backdrop-blur-sm z-10">
        <button v-if="!isSidebarOpen" class="btn btn-ghost btn-sm btn-circle" @click="isSidebarOpen = true">☰</button>
        <button class="btn btn-ghost btn-sm btn-circle" @click="handleClose">×</button>
        <div class="avatar">
          <div class="w-8 rounded-full">
            <img :src="chatStore.characterPhoto" alt="">
          </div>
        </div>
        <span class="font-bold truncate">{{ chatStore.characterName }}</span>
      </header>

      <!-- 聊天区 -->
      <div class="flex-1 relative min-h-0" :style="modalStyle">
        <!-- ChatHistory：只要有真实 sessionId 或是虚拟会话就渲染 -->
        <ChatHistory
          ref="chat-history-ref"
          v-if="chatStore.currentSessionId || chatStore.isVirtualSession"
          :history="chatStore.history"
          :sessionId="chatStore.currentSessionId"
          :character="chatStore.displayCharacter"
          @pushFrontMessage="chatStore.handlePushFrontMessage"
        />
        <!-- InputField：角色未被删除时才能输入 -->
        <InputField
          v-if="chatStore.canChat"
          ref="input-ref"
          @pushBackMessage="handlePushBackMessage"
          @addToLastMessage="handleAddToLastMessage"
          @stopOpeningAudio="audioStore.stop"
          @sessionCreated="handleSessionCreated"
        />
        <!-- 角色被删除后的只读提示 -->
        <div
          v-else-if="chatStore.currentSessionId && !chatStore.canChat"
          class="absolute bottom-0 left-0 right-0 p-4 text-center text-white/80 bg-black/30 backdrop-blur-sm text-sm"
        >
          该角色已被删除，仅支持查看历史记录
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
</style>
