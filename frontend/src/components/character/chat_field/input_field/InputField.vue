<script setup lang="ts">
// InputField: 聊天输入框 + 语音输入 + 流式音频播放（MSE）+ 图片粘贴
import { onUnmounted, ref, useTemplateRef } from 'vue';
import MicIcon from '../../icons/MicIcon.vue';
import SendIcon from '../../icons/SendIcon.vue';
import streamApi from '@/js/http/streamApi'
import api from '@/js/http/api'
import { useChatStore } from '@/stores/chat'
import { useAudioStore } from '@/stores/audio'
import Microphone from './Microphone.vue';

const emit = defineEmits(['pushBackMessage', 'addToLastMessage', 'stopOpeningAudio', 'sessionCreated', 'chatFinished'])

const chatStore = useChatStore()
const audioStore = useAudioStore()
const inputRef = useTemplateRef('input-ref')
const message = ref('')
type ImageItem = { id: string; base64: string; preview: string }
const images = ref<ImageItem[]>([])
let processId = 0
let abortController: AbortController | null = null
const showMic = ref(false)
const isCreatingSession = ref(false)

function focus() {
    inputRef.value?.focus()
}

function stripDataUrlPrefix(dataUrl: string): string {
    const commaIdx = dataUrl.indexOf(',')
    return commaIdx >= 0 ? dataUrl.slice(commaIdx + 1) : dataUrl
}

function compressImage(file: File): Promise<{ base64: string; preview: string }> {
    return new Promise((resolve) => {
        const reader = new FileReader()
        reader.onload = () => {
            const img = new Image()
            img.onload = () => {
                const MAX = 1920
                let w = img.width
                let h = img.height
                if (w > MAX || h > MAX) {
                    if (w > h) { h = Math.round(h * MAX / w); w = MAX }
                    else { w = Math.round(w * MAX / h); h = MAX }
                }
                const canvas = document.createElement('canvas')
                canvas.width = w
                canvas.height = h
                const ctx = canvas.getContext('2d')!
                ctx.drawImage(img, 0, 0, w, h)
                const compressed = canvas.toDataURL('image/jpeg', 0.8)
                resolve({
                    base64: stripDataUrlPrefix(compressed),
                    preview: compressed,
                })
            }
            img.src = reader.result as string
        }
        reader.readAsDataURL(file)
    })
}

async function handlePaste(event: ClipboardEvent) {
    const items = event.clipboardData?.items
    if (!items) return
    let added = false
    for (const item of items) {
        if (item.type.startsWith('image/')) {
            const file = item.getAsFile()
            if (!file) continue
            const result = await compressImage(file)
            images.value.push({
                id: crypto.randomUUID(),
                base64: result.base64,
                preview: result.preview,
            })
            added = true
        }
    }
    if (added) {
        event.preventDefault()
    }
}

function removeImage(id: string) {
    images.value = images.value.filter(img => img.id !== id)
}

async function handleSend(_event?: Event, audio_msg?: string) {
    let content: string
    if(audio_msg) {
        content = audio_msg.trim()
    } else {
        content = message.value.trim()
    }
    if(!content && images.value.length === 0) return

    // 虚拟状态下先创建真实 Session
    let actualSessionId = chatStore.currentSessionId
    if (!actualSessionId && chatStore.friend?.id) {
        if (isCreatingSession.value) return
        isCreatingSession.value = true
        try {
            const res = await api.post('/api/friend/session/create/', {
                friend_id: chatStore.friend.id
            })
            if (res.data.result === 'success') {
                actualSessionId = res.data.session.id
                emit('sessionCreated', res.data.session)
            } else {
                return
            }
        } catch (err) {
            return
        } finally {
            isCreatingSession.value = false
        }
    }
    if (!actualSessionId) return

    // 初始化流式音频通道，播放 AI 的 TTS 语音
    audioStore.initStream()

    const curId = ++ processId

    const currentImages = [...images.value]
    const imagePreviews = currentImages.map(img => img.preview)
    message.value = ''
    images.value = []

    emit('pushBackMessage', { role: 'user', content: content, images: imagePreviews, id: crypto.randomUUID() })
    emit('pushBackMessage', { role: 'ai', content: '', id: crypto.randomUUID() })
    emit('chatFinished')
    abortController = new AbortController()
    try {
        await streamApi('api/friend/message/chat/', {
            signal: abortController.signal,
            body: {
                session_id: actualSessionId,
                message: content,
                images: currentImages.map(img => img.base64),
            },
            onmessage(data, isDone) {
                if( curId != processId) return
                if(data.content) {
                    emit('addToLastMessage', data.content)
                }
                if(data.audio) {
                    audioStore.appendStreamChunk(data.audio)
                }
            },
            onerror(err) {
            }
        })
    } catch (err) {
    } finally {
        abortController = null
    }
}

function close() {
    ++processId
    if (abortController) {
        abortController.abort()
        abortController = null
    }
    showMic.value = false
    audioStore.stop()
}

function abortChat() {
    ++processId
    if (abortController) {
        abortController.abort()
        abortController = null
    }
    audioStore.stop()
}

function handleStop() {
    abortChat()
    emit('stopOpeningAudio')
}

onUnmounted(() => {
    audioStore.stop()
})

defineExpose({
    focus,
    close,
    abortChat,
})
</script>
<template>
    <!-- 图片轮播列表 -->
    <div v-if="images.length > 0" class="absolute bottom-16 left-4 right-4">
        <div class="carousel carousel-center rounded-box bg-base-200/90 backdrop-blur-sm p-2 gap-2">
            <div v-for="img in images" :key="img.id" class="carousel-item relative w-24 h-24 shrink-0">
                <img :src="img.preview" class="w-full h-full object-cover rounded-lg" />
                <button
                    class="absolute -top-1 -right-1 w-5 h-5 flex items-center justify-center rounded-full bg-base-300 hover:bg-error hover:text-white text-xs leading-none transition-colors"
                    @click="removeImage(img.id)"
                >&times;</button>
            </div>
        </div>
    </div>

    <form v-if="!showMic" @submit.prevent="handleSend" class="absolute bottom-4 left-4 right-4 h-12 flex items-center">
        <input
            ref="input-ref"
            v-model="message"
            @paste="handlePaste"
            class="input bg-white/95 text-gray-800 placeholder-gray-400 text-base w-full h-full rounded-2xl pr-20 shadow-lg border border-gray-200/50 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            type="text" placeholder="请输入文本...（支持粘贴图片）">
        <div @click="handleSend" class="absolute right-2 w-8 h-8 flex justify-center items-center cursor-pointer text-gray-600 hover:text-blue-500 transition-colors">
            <SendIcon />
        </div>
        <div @click="showMic = true" class="absolute right-10 w-8 h-8 flex justify-center items-center cursor-pointer text-gray-600 hover:text-blue-500 transition-colors">
            <MicIcon />
        </div>
    </form>
    <Microphone v-else @close="showMic = false" @send="handleSend" @stop="handleStop" />
</template>
<style scoped></style>
