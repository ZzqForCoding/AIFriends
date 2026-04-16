import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * AudioStore: 全局音频播放器（单例）
 *
 * 2026-04 新增：将原本散落在 ChatField / InputField 中的音频逻辑抽离出来，
 * 统一管理三类音频播放场景：
 *   1. 普通完整音频（开场白朗读、消息朗读按钮）
 *   2. SSE 流式 TTS 音频（AI 回复时边生成边播放）
 *   3. 未来可扩展的单条消息朗读
 *
 * 核心保证：播放新音频前必须先 stop() 清理旧音频，
 * 避免"切换会话时旧音频仍在播放"、"新消息与旧消息声音叠加"等问题。
 */
export const useAudioStore = defineStore('audio', () => {
  // ==================== 普通音频播放器 ====================
  // 用于开场白、朗读按钮等已经完整的音频文件
  const player = ref<HTMLAudioElement | null>(null)

  // ==================== MSE 流式播放相关状态 ====================
  // 用于 SSE 流式 TTS：阿里云百炼 TTS 返回的是 base64 音频片段，
  // 通过 MediaSource + SourceBuffer 实现边收边播。
  let mediaSource: MediaSource | null = null
  let sourceBuffer: SourceBuffer | null = null
  let audioQueue: Uint8Array[] = []
  let isUpdating = false

  // ==================== 公共方法 ====================

  /**
   * 停止并清理所有音频资源
   * 调用场景：
   *   - 切换会话 / 关闭弹窗
   *   - 用户点击停止按钮
   *   - 播放新音频前（playUrl / initStream 内部会自动先调用）
   */
  function stop() {
    // 1. 停止普通音频
    if (player.value) {
      player.value.pause()
      player.value.src = ''
      player.value = null
    }

    // 2. 停止并清理 MSE 流式音频
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

  /**
   * 播放普通音频（完整 URL）
   * 例如：开场白 TTS 返回的 mp3 链接、消息朗读接口返回的音频链接
   */
  function playUrl(url: string) {
    stop()
    const audio = new Audio(url)
    player.value = audio
    audio.play().catch(e => console.error('音频播放失败', e))
  }

  /**
   * 初始化 MSE 流式音频通道
   * 在发起 SSE 聊天请求前先调用，建立好 MediaSource 和 Audio 对象，
   * 后续通过 appendStreamChunk() 不断追加音频片段。
   */
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

  /**
   * 向 MSE 队列追加音频片段（base64 字符串）
   * 由 InputField 在 SSE onmessage 中收到 data.audio 时调用。
   */
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

  /** 内部：消费 MSE 队列，按顺序把音频片段 append 到 SourceBuffer */
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
