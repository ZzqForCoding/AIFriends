<script setup lang="ts">
/**
 * ChatHistory: 聊天消息滚动区域
 *
 * 2026-04 大改说明：
 *   1. 从原来的"自动 onMounted 加载"改为"受控加载"。
 *      初始加载完全由外部 ChatField 通过 resetAndLoad() 触发，
 *      避免 FriendIndex 中多个 Character 同时挂载 ChatField 时，
 *      每个 ChatHistory 都自动发起 get_history 请求。
 *   2. resetAndLoad() 会真正重置 lastMessageId / hasMessages / isLoading，
 *      解决切换 Session 后 lastMessageId 残留导致历史加载为空或缺失的 bug。
 *   3. 空 user_message 保护：后端把开场白存为 user_message='' 的 Message，
 *      前端加载历史时跳过 push 空的用户气泡。
 *   4. IntersectionObserver 的 root 改为 scrollRef.value（滚动容器本身），
 *      而不是浏览器视口，保证无限滚动只在聊天区内生效。
 */
import { nextTick, onBeforeUnmount, onMounted, useTemplateRef } from 'vue';
import Message from './message/Message.vue';
import api from '@/js/http/api';

const props = defineProps(['history', 'sessionId', 'character'])
const emit = defineEmits(['pushFrontMessage'])

const scrollRef = useTemplateRef<HTMLDivElement>('scroll-ref')
const sentinelRef = useTemplateRef<HTMLDivElement>('sentinel-ref')

// 加载状态：防止并发请求、标记是否还有更早消息
let isLoading = false
let hasMessages = true
// 用于后端分页：0 表示第一次加载，之后取已加载消息中最小的 id
let lastMessageId = 0

/** 判断顶部哨兵元素是否仍位于滚动容器可视区域内 */
function checkSentinelVisible() {
  if (!sentinelRef.value || !scrollRef.value) return false
  const sentinelRect = sentinelRef.value.getBoundingClientRect()
  const scrollRect = scrollRef.value.getBoundingClientRect()
  return sentinelRect.top < scrollRect.bottom && sentinelRect.bottom > scrollRect.top
}

/**
 * 加载更多历史消息（向上滚动触发）
 * 后端按 id 倒序返回最近 10 条，前端 prepend 到 history 数组顶部。
 * 加载完成后通过"旧高度差"修正 scrollTop，保持用户视觉位置不动。
 */
async function loadMore() {
  if (isLoading || !hasMessages) return
  if (!props.sessionId) return
  isLoading = true

  let newMessages: any[] = []
  try {
    const res = await api.get('/api/friend/message/get_history/', {
      params: {
        last_message_id: lastMessageId,
        session_id: props.sessionId
      }
    })
    const data = res.data
    if (data.result === 'success') {
      newMessages = data.messages
    }
  } catch (err) {
    // 静默失败，避免打断用户浏览历史
  } finally {
    isLoading = false

    if (newMessages.length === 0) {
      hasMessages = false
    } else {
      const oldHeight = scrollRef.value?.scrollHeight ?? 0
      const oldTop = scrollRef.value?.scrollTop ?? 0

      for (const m of newMessages) {
        // AI 回复消息
        emit('pushFrontMessage', {
          role: 'ai',
          content: m.output,
          id: crypto.randomUUID()
        })
        // 开场白消息的 user_message 为空，需要跳过，否则会出现空白用户气泡
        if (m.user_message) {
          emit('pushFrontMessage', {
            role: 'user',
            content: m.user_message,
            id: crypto.randomUUID()
          })
        }
        lastMessageId = m.id
      }

      await nextTick()
      const newHeight = scrollRef.value?.scrollHeight ?? 0
      const el = scrollRef.value
      if (el) {
        // 修正滚动位置：内容增高了多少，scrollTop 就增加多少，
        // 这样用户看到的仍是刚才那条消息，而不是被推到下方
        el.scrollTop = oldTop + newHeight - oldHeight
      }

      // 如果追加后哨兵仍可见，说明一屏没装满，继续加载直到装满或没有更多
      if (checkSentinelVisible()) {
        await loadMore()
      }
    }
  }
}

/** 强制滚动到底部（发送新消息、AI 流式输出完成时使用） */
async function scrollToBottom() {
  await nextTick()
  const el = scrollRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

/** 判断用户当前是否已经在底部附近（50px 以内） */
function isNearBottom() {
  const el = scrollRef.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight < 50
}

/**
 * 智能滚动：仅当用户已经在底部时才自动滚底。
 * 若用户主动上滑查看历史，则保持当前位置不动，防止打断阅读。
 */
async function smartScrollToBottom() {
  if (isNearBottom()) {
    await scrollToBottom()
  }
}

/**
 * 重置并加载：切换 Session 时调用。
 * 必须同时重置 lastMessageId / hasMessages / isLoading，
 * 否则上一个 Session 的 lastMessageId 会污染新 Session 的分页查询。
 */
async function resetAndLoad() {
  lastMessageId = 0
  hasMessages = true
  isLoading = false
  await loadMore()
}

let observer: IntersectionObserver | null = null

/**
 * 组件挂载时：只注册 IntersectionObserver，不主动加载历史。
 * 历史加载时机由 ChatField.showModal() / switchAndLoadSession() 等通过 resetAndLoad() 控制。
 */
onMounted(() => {
  observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          loadMore()
        }
      })
    },
    // root 必须是滚动容器本身，不能用 null（浏览器视口），
    // 否则聊天区还没滚动到页面顶部就会误触发加载
    { root: scrollRef.value, rootMargin: '2px', threshold: 0 }
  )

  if (sentinelRef.value) {
    observer.observe(sentinelRef.value)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
})

defineExpose({
  scrollToBottom,
  smartScrollToBottom,
  resetAndLoad
})
</script>

<template>
  <!-- 聊天滚动区：绝对定位填充主区域，底部留出 input 高度（bottom-20） -->
  <div ref="scroll-ref" class="absolute inset-x-2 top-4 bottom-20 overflow-y-auto pr-1">
    <!-- 顶部哨兵：当滚动到顶部时触发 loadMore 加载更早消息 -->
    <div ref="sentinel-ref" class="h-2"></div>
    <Message
      v-for="message in history"
      :key="message.id"
      :message="message"
      :character="character"
    />
  </div>
</template>

<style scoped>
/* 自定义滚动条样式，显示在右侧 */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.5);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(156, 163, 175, 0.8);
}
</style>
