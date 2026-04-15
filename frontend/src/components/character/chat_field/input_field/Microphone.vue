<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import KeyboardIcon from '../../icons/KeyboardIcon.vue';
import { MicVAD } from '@ricky0123/vad-web';
import api from '@/js/http/api';

const emit = defineEmits(['close', 'send', 'stop'])

const isSpeaking = ref(false)

let vadInstance: MicVAD | null = null;

const startRecording = async () => {
  const baseUrl = "http://127.0.0.1:8000/static/frontend/vad/";
  try {
    vadInstance = await MicVAD.new({
      baseAssetPath: baseUrl,
      onSpeechStart: () => {
        isSpeaking.value = true;
        emit('stop')
      },
      onSpeechEnd: (audio) => {
        isSpeaking.value = false;
        const pcm16 = float32ToInt16(audio);
        sendToBackend(pcm16);
      },
      ortConfig: (ort) => {
        ort.env.wasm.wasmPaths = baseUrl;
        ort.env.logLevel = "error";
      },
      positiveSpeechThreshold: 0.8,
      negativeSpeechThreshold: 0.65,
      minSpeechMs: 100,
      redemptionMs: 100,
    });

    await vadInstance.start();
  } catch (e) {
    console.error("VAD 初始化失败:", e);
  }
};
// 将 Float32 转 PCM 16-bit
const float32ToInt16 = (float32Array: Float32Array): ArrayBuffer => {
  const buffer = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const val = float32Array[i];
    if (val === undefined) continue;
    let s = Math.max(-1, Math.min(1, val));
    buffer[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return buffer.buffer;
};

const sendToBackend = async (arrayBuffer: ArrayBuffer) => {
  // 将音频发送到后端
  const blob = new Blob([arrayBuffer], { type: "audio/pcm" })
  const formData = new FormData()
  formData.append('audio', blob, 'voice.pcm')
  
  try {
    const res = await api.post('/api/friend/message/asr/asr/', formData)
    const data = res.data
    if(data.result === 'success') {
        emit('send', null, data.text)
    }
  } catch (err) {
  }
};

onMounted(() => {
  startRecording()
})

onBeforeUnmount(() => {
  if (vadInstance) {
    vadInstance.destroy()
    vadInstance = null
  }
})
</script>
<template>
    <div class="absolute bottom-4 left-4 right-4 h-12 flex items-center bg-white/95 rounded-2xl shadow-lg border border-gray-200/50">
        <div v-if="isSpeaking" class="flex items-center justify-center gap-1 h-6 flex-1">
            <div v-for="i in 32" :key="i" class="w-0.5 bg-primary rounded-full animate-wave"
                :style="{ animationDelay: `${i * 0.1}s` }"></div>
        </div>
        <div v-else class="text-gray-400 text-base w-full text-center">
            语音输入
        </div>
        <div @click="emit('close')" class="absolute right-2 w-8 h-8 flex justify-center items-center cursor-pointer text-gray-600 hover:text-blue-500 transition-colors">
            <KeyboardIcon />
        </div>
    </div>
</template>
<style scoped>
.animate-wave {
  height: 4px;
  animation: wave-animation 0.6s ease-in-out infinite alternate;
}

@keyframes wave-animation {
  0% { height: 4px; opacity: 0.3; }
  100% { height: 20px; opacity: 1; }
}
</style>
