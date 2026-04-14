<script setup lang="ts">
import { onUnmounted, ref, useTemplateRef } from 'vue';
import MicIcon from '../../icons/MicIcon.vue';
import SendIcon from '../../icons/SendIcon.vue';
import streamApi from '@/js/http/streamApi'
import Microphone from './Microphone.vue';

const props = defineProps(['friendId'])
const emit = defineEmits(['pushBackMessage', 'addToLastMessage', 'stopOpeningAudio'])

const inputRef = useTemplateRef('input-ref')
const message = ref('')
let processId = 0
const showMic = ref(false)

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

    initAudioStream()

    const curId = ++ processId

    message.value = ''

    emit('pushBackMessage', {role: 'user', content: content, id: crypto.randomUUID()})
    emit('pushBackMessage', {role: 'ai', content: '', id: crypto.randomUUID()})

    try {
        await streamApi('api/friend/message/chat/', {
            body: {
                friend_id: props.friendId,
                message: content,
            },
            onmessage(data, isDone) {
                if( curId != processId) return
                if(data.content) {
                    emit('addToLastMessage', data.content)
                }
                if(data.audio) {
                    handleAudioChunk(data.audio)
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
    stopAudio()
}

function handleStop() {
    ++processId
    stopAudio()
    emit('stopOpeningAudio')
}

let mediaSource: MediaSource | null = null;
let sourceBuffer: SourceBuffer | null = null;
const audioPlayer = new Audio(); // 全局播放器实例
let audioQueue: Uint8Array[] = [];           // 待写入 Buffer 的二进制队列
let isUpdating: boolean = false;        // Buffer 是否正在写入

const initAudioStream = (): void => {
    audioPlayer.pause();
    audioQueue = [];
    isUpdating = false;

    mediaSource = new MediaSource();
    audioPlayer.src = URL.createObjectURL(mediaSource);

    mediaSource.addEventListener('sourceopen', () => {
        try {
            sourceBuffer = mediaSource!.addSourceBuffer('audio/mpeg');
            sourceBuffer.addEventListener('updateend', () => {
                isUpdating = false;
                processQueue();
            });
        } catch (e) {
            console.error("MSE AddSourceBuffer Error:", e);
        }
    });

    audioPlayer.play().catch(e => console.error("等待用户交互以播放音频"));
};

const processQueue = (): void => {
    if (isUpdating || audioQueue.length === 0 || !sourceBuffer || sourceBuffer.updating) {
        return;
    }

    isUpdating = true;
    const chunk = audioQueue.shift();
    if (!chunk) {
        isUpdating = false;
        return;
    }
    try {
        sourceBuffer.appendBuffer(chunk.buffer as ArrayBuffer);
    } catch (e) {
        console.error("SourceBuffer Append Error:", e);
        isUpdating = false;
    }
};

const stopAudio = (): void => {
    audioPlayer.pause();
    audioQueue = [];
    isUpdating = false;

    if (mediaSource) {
        if (mediaSource.readyState === 'open') {
            try {
                mediaSource.endOfStream();
            } catch (e) {
            }
        }
        mediaSource = null;
    }

    if (audioPlayer.src) {
        URL.revokeObjectURL(audioPlayer.src);
        audioPlayer.src = '';
    }
};

const handleAudioChunk = (base64Data: string): void => {  // 将语音片段添加到播放器队列中
    try {
        const binaryString = atob(base64Data);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        audioQueue.push(bytes);
        processQueue();
    } catch (e) {
        console.error("Base64 Decode Error:", e);
    }
};

onUnmounted(() => {
    audioPlayer.pause();
    audioPlayer.src = '';
});

defineExpose({
    focus,
    close
})
</script>
<template>
    <form v-if="!showMic" @submit.prevent="handleSend" class="absolute bottom-4 left-2 h-12 w-86 flex items-center">
        <input
            ref="input-ref"
            v-model="message"
            class="input bg-black/30 backdrop-blur-sm text-white text-base w-full h-full rounded-2xl pr-20"
            type="text" placeholder="请输入文本...">
        <div @click="handleSend" class="absolute right-2 w-8 h-8 flex justify-center items-center cursor-pointer">
            <SendIcon />
        </div>
        <div @click="showMic = true" class="absolute right-10 w-8 h-8 flex justify-center items-center cursor-pointer">
            <MicIcon />
        </div>
    </form>
    <Microphone v-else @close="showMic = false" @send="handleSend" @stop="handleStop" />
</template>
<style scoped></style>
