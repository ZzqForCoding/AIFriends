<script setup lang="ts">
/**
 * InfiniteScroll: 通用无限滚动容器
 *
 * 2026-04 新增组件， originally 是为了在 FriendIndex / ChatHistory 等列表中复用
 * IntersectionObserver + 加载触发的逻辑。
 *
 * 设计要点：
 *   1. 通过 sentinel（哨兵元素）的位置判断是否需要加载更多。
 *   2. sentinel 可以放在顶部（向上滚动加载历史）或底部（向下滚动加载新内容）。
 *   3. 内置 100ms 防抖标志位，防止同一帧内重复触发 load-more。
 *   4. expose 了滚动相关方法（scrollToBottom / smartScrollToBottom 等），
 *      方便父组件直接通过 ref 调用。
 *
 * 注意：当前 ChatHistory.vue 由于需要更精细的滚动位置修正（加载历史后保持视口不动），
 *       没有直接使用本组件，但 Homepage / FriendIndex 等其他列表场景可以继续复用。
 */
import { onBeforeUnmount, onMounted, ref, useTemplateRef } from 'vue'

const props = defineProps<{
  hasMore?: boolean
  sentinelPosition?: 'top' | 'bottom'
}>()

const emit = defineEmits<{
  'load-more': []
}>()

const containerRef = useTemplateRef<HTMLDivElement>('container-ref')
const sentinelRef = useTemplateRef<HTMLDivElement>('sentinel-ref')

let observer: IntersectionObserver | null = null
let isTriggered = false

/** 手动校验哨兵是否位于容器可视区域内（备用校验） */
function checkSentinelVisible() {
  if (!sentinelRef.value || !containerRef.value) return false
  const sentinelRect = sentinelRef.value.getBoundingClientRect()
  const containerRect = containerRef.value.getBoundingClientRect()
  return sentinelRect.top < containerRect.bottom && sentinelRect.bottom > containerRect.top
}

onMounted(() => {
  observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting && props.hasMore !== false) {
          // 防止同一帧内重复触发 load-more
          if (isTriggered) return
          isTriggered = true
          emit('load-more')
          // 简单防抖：100ms 后重置标志
          setTimeout(() => { isTriggered = false }, 100)
        }
      })
    },
    { root: containerRef.value, rootMargin: '2px', threshold: 0 }
  )
  if (sentinelRef.value) {
    observer.observe(sentinelRef.value)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
})

function scrollToBottom() {
  const el = containerRef.value
  if (el) el.scrollTop = el.scrollHeight
}

function scrollToTop() {
  const el = containerRef.value
  if (el) el.scrollTop = 0
}

function isNearBottom(threshold = 50) {
  const el = containerRef.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight < threshold
}

async function smartScrollToBottom() {
  if (isNearBottom()) {
    scrollToBottom()
  }
}

defineExpose({
  scrollToBottom,
  scrollToTop,
  smartScrollToBottom,
  isNearBottom,
  checkSentinelVisible,
  get container() { return containerRef.value }
})
</script>

<template>
  <div ref="container-ref" class="overflow-y-auto">
    <div v-if="sentinelPosition === 'top'" ref="sentinel-ref" class="h-2 shrink-0"></div>
    <slot></slot>
    <div v-if="sentinelPosition === 'bottom'" ref="sentinel-ref" class="h-2 shrink-0"></div>
  </div>
</template>

<style scoped>
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
