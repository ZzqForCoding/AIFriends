<script setup lang="ts">
// InputField: 聊天输入框 + 语音输入 + 流式音频播放（MSE）
// 核心改动：支持"懒创建会话"——若当前是虚拟新对话（currentSessionId === null），
// 则在用户点击发送时先调用 /api/friend/session/create/ 创建真实 Session，再发起 SSE 聊天
import { onUnmounted, ref, useTemplateRef } from 'vue';
import MicIcon from '../../icons/MicIcon.vue';
import SendIcon from '../../icons/SendIcon.vue';
import streamApi from '@/js/http/streamApi'
import api from '@/js/http/api'
import { useChatStore } from '@/stores/chat'
import { useAudioStore } from '@/stores/audio'
import Microphone from './Microphone.vue';

const emit = defineEmits(['pushBackMessage', 'addToLastMessage', 'stopOpeningAudio', 'sessionCreated'])

const chatStore = useChatStore()
const audioStore = useAudioStore()
const inputRef = useTemplateRef('input-ref')
const message = ref('')
// processId 用于打断旧的 SSE 连接（切换会话或关闭弹窗时 ++processId）
let processId = 0
const showMic = ref(false)
const isCreatingSession = ref(false)

function focus() {
    inputRef.value?.focus()
}

async function handleSend(_event?: Event, audio_msg?: string) {
    let content: string
    if(audio_msg) {
        content = audio_msg.trim()
    } else {
        content = message.value.trim()
    }
    if(!content) return

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

    message.value = ''

    emit('pushBackMessage', {role: 'user', content: content, id: crypto.randomUUID()})
    emit('pushBackMessage', {role: 'ai', content: '', id: crypto.randomUUID()})

    try {
        await streamApi('api/friend/message/chat/', {
            body: {
                session_id: actualSessionId,
                message: content,
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
    }
}

function close() {
    ++processId
    showMic.value = false
    audioStore.stop()
}

// 中断当前正在进行的流式对话：停止音频 + 忽略后续 SSE 回调
function abortChat() {
    ++processId
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
    <form v-if="!showMic" @submit.prevent="handleSend" class="absolute bottom-4 left-4 right-4 h-12 flex items-center">
        <input
            ref="input-ref"
            v-model="message"
            class="input bg-white/95 text-gray-800 placeholder-gray-400 text-base w-full h-full rounded-2xl pr-20 shadow-lg border border-gray-200/50 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            type="text" placeholder="请输入文本...">
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
