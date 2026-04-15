<script setup lang="ts">
// ChatField: 聊天弹窗主容器
// 2026-04 重构说明：
//   1. 所有会话状态（friend/sessions/history/currentSessionId）迁移到 Pinia useChatStore
//   2. 本组件只负责 UI 布局、DOM ref 管理和事件转发
//   3. 核心交互逻辑（懒创建、切换会话、删除会话）全部下沉到 store
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue';
import InputField from './input_field/InputField.vue';
import ChatHistory from './chat_history/ChatHistory.vue';
import { useChatStore } from '@/stores/chat';
import { useAudioStore } from '@/stores/audio';

const chatStore = useChatStore()
const audioStore = useAudioStore()
const inputRef = useTemplateRef('input-ref')
const chatHistoryRef = useTemplateRef('chat-history-ref')
// 侧边栏展开状态保留在组件层，因为只影响本组件布局
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

async function switchAndLoadSession(sessionId: number) {
  await chatStore.switchSession(sessionId)
  await nextTick()
  chatHistoryRef.value?.resetAndLoad()
  inputRef.value?.focus()
}

// 新建会话前先中断当前可能正在进行的流式输出和音频
function handleCreateSession() {
  inputRef.value?.abortChat()
  audioStore.stop()
  chatStore.createSession()
}

async function showModal() {
  chatStore.showModal()
  await nextTick()
  inputRef.value?.focus()
}

function handleClose() {
  chatStore.closeModal()
  inputRef.value?.close()
}

// 用户发送新消息时：先入 history，再智能滚底（仅当用户已在底部时才滚）
function handlePushBackMessage(msg: any) {
  chatStore.handlePushBackMessage(msg)
  chatHistoryRef.value?.smartScrollToBottom()
}

// AI 流式回复增量时：同上，只在底部时自动滚底，防止打断用户查看历史
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
    <!-- 左侧 Sidebar -->
    <aside
      class="bg-base-200 border-r border-base-300 flex flex-col transition-all duration-300 shrink-0"
      :class="isSidebarOpen ? 'w-64' : 'w-0 overflow-hidden'"
    >
      <div class="h-16 flex items-center justify-between px-4 border-b border-base-300 shrink-0">
        <span class="font-bold">历史对话</span>
        <div class="flex items-center gap-1">
          <button v-if="chatStore.canChat && !chatStore.isVirtualSession" class="btn btn-ghost btn-sm btn-circle" @click="handleCreateSession" title="新建对话">+</button>
          <button class="btn btn-ghost btn-sm btn-circle" @click="isSidebarOpen = false">←</button>
        </div>
      </div>
      <div class="flex-1 overflow-y-auto p-2 space-y-1">
        <div
          v-if="chatStore.isVirtualSession"
          class="p-2 rounded-lg cursor-pointer transition-colors flex items-center justify-between bg-primary text-primary-content font-medium"
        >
          <span class="truncate">新的对话</span>
        </div>
        <div
          v-for="session in chatStore.sessions"
          :key="session.id"
          class="p-2 rounded-lg cursor-pointer transition-colors flex items-center justify-between group"
          :class="session.id === chatStore.currentSessionId ? 'bg-primary text-primary-content font-medium' : 'bg-base-100 hover:bg-base-300'"
          @click="switchAndLoadSession(session.id)"
        >
          <span class="truncate">{{session.session_name}}</span>
          <button
            class="btn btn-ghost btn-xs btn-circle opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-1"
            :class="session.id === chatStore.currentSessionId ? 'text-white/80 hover:text-white hover:bg-white/20' : 'text-base-content hover:bg-base-300'"
            @click.stop="chatStore.deleteSession(session.id)"
            title="删除"
          >×</button>
        </div>
      </div>
    </aside>

    <!-- 右侧主区域 -->
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
        <ChatHistory
          ref="chat-history-ref"
          v-if="chatStore.currentSessionId || chatStore.isVirtualSession"
          :history="chatStore.history"
          :sessionId="chatStore.currentSessionId"
          :character="chatStore.displayCharacter"
          @pushFrontMessage="chatStore.handlePushFrontMessage"
        />
        <InputField
          v-if="chatStore.canChat"
          ref="input-ref"
          @pushBackMessage="handlePushBackMessage"
          @addToLastMessage="handleAddToLastMessage"
          @stopOpeningAudio="audioStore.stop"
          @sessionCreated="chatStore.handleSessionCreated"
        />
        <div v-else-if="chatStore.currentSessionId && !chatStore.canChat" class="absolute bottom-0 left-0 right-0 p-4 text-center text-white/80 bg-black/30 backdrop-blur-sm text-sm">
          该角色已被删除，仅支持查看历史记录
        </div>
      </div>
    </main>
  </div>
</template>
<style scoped>
</style>
