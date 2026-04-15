<script setup lang="ts">
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
          // 防止同一帧内重复触发
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
