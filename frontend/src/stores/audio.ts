import { defineStore } from 'pinia'
import { ref } from 'vue'

// 全局音频播放器（单例）
// 负责统一管理：开场白音频、流式 TTS 音频、未来单条消息朗读音频
// 核心保证：播放新音频前必须先停止旧音频，避免多处声音叠加
export const useAudioStore = defineStore('audio', () => {
  // 普通音频播放器（用于开场白、朗读按钮等完整音频文件）
  const player = ref<HTMLAudioElement | null>(null)

  // MSE 流式播放相关状态（用于 SSE 流式 TTS）
  let mediaSource: MediaSource | null = null
  let sourceBuffer: SourceBuffer | null = null
  let audioQueue: Uint8Array[] = []
  let isUpdating = false

  // 停止并清理所有音频资源（普通音频 + MSE 流式）
  function stop() {
    // 1. 停止普通音频
    if (player.value) {
      player.value.pause()
      player.value.src = ''
      player.value = null
    }

    // 2. 停止 MSE 流式音频
    audioQueue = []
    isUpdating = false
    if (mediaSource) {
      if (mediaSource.readyState === 'open') {
        try {
          mediaSource.endOfStream()
        } catch (e) {}
      }
      mediaSource = null
    }
    sourceBuffer = null
  }

  // 播放普通音频（如开场白、消息朗读）
  function playUrl(url: string) {
    stop()
    const audio = new Audio(url)
    player.value = audio
    audio.play().catch(e => console.error('音频播放失败', e))
  }

  // 初始化 MSE 流式音频通道（在发起 SSE 前调用）
  function initStream() {
    stop()
    mediaSource = new MediaSource()
    const audio = new Audio()
    audio.src = URL.createObjectURL(mediaSource)
    player.value = audio

    mediaSource.addEventListener('sourceopen', () => {
      try {
        sourceBuffer = mediaSource!.addSourceBuffer('audio/mpeg')
        sourceBuffer.addEventListener('updateend', () => {
          isUpdating = false
          processQueue()
        })
      } catch (e) {
        console.error('MSE AddSourceBuffer Error:', e)
      }
    })

    audio.play().catch(e => console.error('等待用户交互以播放音频'))
  }

  // 向 MSE 队列追加音频片段（base64）
  function appendStreamChunk(base64Data: string) {
    try {
      const binaryString = atob(base64Data)
      const len = binaryString.length
      const bytes = new Uint8Array(len)
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }
      audioQueue.push(bytes)
      processQueue()
    } catch (e) {
      console.error('Base64 Decode Error:', e)
    }
  }

  // 内部：消费 MSE 队列
  function processQueue() {
    if (isUpdating || audioQueue.length === 0 || !sourceBuffer || sourceBuffer.updating) {
      return
    }
    isUpdating = true
    const chunk = audioQueue.shift()
    if (!chunk) {
      isUpdating = false
      return
    }
    try {
      sourceBuffer.appendBuffer(chunk.buffer as ArrayBuffer)
    } catch (e) {
      console.error('SourceBuffer Append Error:', e)
      isUpdating = false
    }
  }

  return {
    stop,
    playUrl,
    initStream,
    appendStreamChunk,
  }
})
