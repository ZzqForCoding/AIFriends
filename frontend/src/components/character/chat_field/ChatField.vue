<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue';
import InputField from './input_field/InputField.vue';
import CharacterPhotoField from './character_photo_field/CharacterPhotoField.vue';
import ChatHistory from './chat_history/ChatHistory.vue';
import api from '@/js/http/api';

const props = defineProps(['friend'])

const modalRef = useTemplateRef<HTMLDialogElement>('modal-ref')
const inputRef = useTemplateRef('input-ref')
const chatHistoryRef = useTemplateRef('chat-history-ref')
const history = ref<any>([])
const hasPlayedOpening = ref(false)   // 是否播放开场白
const openingAudio = ref<HTMLAudioElement | null>(null)   // 正在播放的语音

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
    stopOpeningAudio()
    modalRef.value?.showModal()
    await nextTick()
    inputRef.value?.focus()
}

function handleClose() {
  stopOpeningAudio()
  modalRef.value?.close()
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
    <dialog ref="modal-ref" class="modal">
        <div class="modal-box w-90 h-150" :style="modalStyle">
            <button @click="handleClose" class="btn btn-circle btn-sm btn-ghost bg-transparent absolute right-2 top-2">x</button>
            <ChatHistory ref="chat-history-ref" v-if="friend" :history="history" :friendId="friend.id" :character="friend.character"  @pushFrontMessage="handlePushFrontMessage"  />
            <InputField v-if="friend" ref="input-ref" :friendId="friend.id" @pushBackMessage="handlePushBackMessage" @addToLastMessage="handleAddToLastMessage" />
            <CharacterPhotoField v-if="friend" :character="friend.character" />
        </div>
    </dialog>
</template>
<style scoped>

</style>
