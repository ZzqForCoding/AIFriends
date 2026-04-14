<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue';
import InputField from './input_field/InputField.vue';
import CharacterPhotoField from './character_photo_field/CharacterPhotoField.vue';
import ChatHistory from './chat_history/ChatHistory.vue';
import api from '@/js/http/api';

const props = defineProps(['friend'])

const inputRef = useTemplateRef('input-ref')
const chatHistoryRef = useTemplateRef('chat-history-ref')
const history = ref<any>([])
const hasPlayedOpening = ref(false)   // 是否播放开场白
const openingAudio = ref<HTMLAudioElement | null>(null)   // 正在播放的语音
const isOpen = ref(false)
const isSidebarOpen = ref(true)

const modalStyle = computed(() => {
  if (props.friend) {
    return {
      backgroundImage: `url(${props.friend.character.background_image})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat',
    }
  } else {
    return {}
  }
})

function handlePushBackMessage(msg: string) {
  history.value.push(msg)
  chatHistoryRef.value?.scrollToBottom()
}

function handleAddToLastMessage(delta: string) {
    history.value.at(-1).content += delta
  chatHistoryRef.value?.scrollToBottom()
}

function handlePushFrontMessage(msg: any) {
  history.value.unshift(msg)
}

function stopOpeningAudio() {
  if (openingAudio.value) {
    openingAudio.value.pause()
    openingAudio.value.src = ''
    openingAudio.value.onended = null
    openingAudio.value = null
  }
}

async function showModal() {
    history.value = []
    hasPlayedOpening.value = false
    stopOpeningAudio()
    isOpen.value = true
    await nextTick()
    inputRef.value?.focus()
}

function handleClose() {
  stopOpeningAudio()
  isOpen.value = false
  inputRef.value?.close()
}

watch(history, (val) => {
  if (hasPlayedOpening.value) return
  if (
    val.length === 2 &&
    val[0].role === 'user' && val[0].content === '' &&
    val[1].role === 'ai'
  ) {
    hasPlayedOpening.value = true
    const text = val[1].content
    api.post('/api/friend/message/tts/tts/', { text })
      .then(res => {
        if (res.data.result === 'success' && res.data.audio) {
          stopOpeningAudio()
          openingAudio.value = new Audio('data:audio/mp3;base64,' + res.data.audio)
          openingAudio.value.onended = () => {
            openingAudio.value = null
          }
          return openingAudio.value.play()
        }
      })
      .catch(e => console.error('开场白语音播放失败', e))
  }
}, { deep: true })

defineExpose({
    showModal
})
</script>
<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex bg-base-100">
    <!-- 左侧 Sidebar -->
    <aside
      class="bg-base-200 border-r border-base-300 flex flex-col transition-all duration-300 shrink-0"
      :class="isSidebarOpen ? 'w-64' : 'w-0 overflow-hidden'"
    >
      <div class="h-16 flex items-center justify-between px-4 border-b border-base-300 shrink-0">
        <span class="font-bold">历史对话</span>
        <button class="btn btn-ghost btn-sm btn-circle" @click="isSidebarOpen = false">←</button>
      </div>
      <div class="flex-1 overflow-y-auto p-2 space-y-1">
        <div class="p-2 rounded-lg bg-base-100 cursor-pointer hover:bg-base-300">
          当前对话
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
                <img :src="friend?.character.photo" alt="">
            </div>
        </div>
        <span class="font-bold truncate">{{ friend?.character?.name }}</span>
      </header>

      <!-- 聊天区 -->
      <div class="flex-1 relative min-h-0" :style="modalStyle">
        <ChatHistory ref="chat-history-ref" v-if="friend" :history="history" :friendId="friend.id" :character="friend.character" @pushFrontMessage="handlePushFrontMessage" />
        <InputField v-if="friend" ref="input-ref" :friendId="friend.id" @pushBackMessage="handlePushBackMessage" @addToLastMessage="handleAddToLastMessage" @stopOpeningAudio="stopOpeningAudio" />
        <!-- <CharacterPhotoField v-if="friend" :character="friend.character" /> -->
      </div>
    </main>
  </div>
</template>
<style scoped>
</style>
