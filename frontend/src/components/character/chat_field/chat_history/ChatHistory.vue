<script setup lang="ts">
import { nextTick, onBeforeMount, onBeforeUnmount, onMounted, useTemplateRef, watch } from 'vue';
import Message from './message/Message.vue';
import api from '@/js/http/api';

const props = defineProps(['history', 'sessionId', 'character'])
const emit = defineEmits(['pushFrontMessage'])
const scrollRef = useTemplateRef('scroll-ref')
const sentinelRef = useTemplateRef('sentinel-ref')
let isLoading = false
let hasMessages = true
let lastMessageId = 0

function checkSentinelVisible() {  // 判断哨兵是否能被看到
  if (!sentinelRef.value) return false

  const sentinelRect = sentinelRef.value.getBoundingClientRect()
  const scrollRect = scrollRef.value!.getBoundingClientRect()
  return sentinelRect.top < scrollRect.bottom && sentinelRect.bottom > scrollRect.top
}

async function loadMore() {
    if(isLoading || !hasMessages) return
    if(!props.sessionId) return
    isLoading = true

    let newMessages = []
    try {
        const res = await api.get('/api/friend/message/get_history/', {
            params: {
                last_message_id: lastMessageId,
                session_id: props.sessionId
            }
        })
        const data = res.data
        if(data.result === 'success') {
            newMessages = data.messages
        }
    } catch(err) {
    } finally {
        isLoading = false

        if(newMessages.length === 0) {
            hasMessages = false
        } else {
            const oldHeight = scrollRef.value?.scrollHeight
            const oldTop = scrollRef.value?.scrollTop
            for(const m of newMessages) {
                emit('pushFrontMessage', {
                    role: 'ai',
                    content: m.output,
                    id: crypto.randomUUID()
                })
                emit('pushFrontMessage', {
                    role: 'user',
                    content: m.user_message,
                    id: crypto.randomUUID()
                })
                lastMessageId = m.id
            }

            await nextTick()
            const newHeight = scrollRef.value?.scrollHeight
            const el = scrollRef.value
            if(el) {
                el.scrollTop = oldTop! + newHeight! - oldHeight!
            }

            if(checkSentinelVisible()) {
                await loadMore()
            }
        }
    }
}

async function scrollToBottom() {
    await nextTick()
    const el = scrollRef.value
    if (el) {
        el.scrollTop = el.scrollHeight
    }
}

// 判断用户当前是否已经在底部附近（50px 以内）
function isNearBottom() {
    const el = scrollRef.value
    if (!el) return true
    return el.scrollHeight - el.scrollTop - el.clientHeight < 50
}

// 智能滚动：仅当用户已经在底部时才自动滚底，
// 若用户主动上滑查看历史，则保持当前位置不动
async function smartScrollToBottom() {
    if (isNearBottom()) {
        await scrollToBottom()
    }
}

let observer: any = null
onMounted(() => {
    observer = new IntersectionObserver(
        entries => {
            entries.forEach(entry => {
                if(entry.isIntersecting) {
                    loadMore()
                }
            })
        },
        {root: null, rootMargin: '2px', threshold: 0}
    )

    if (sentinelRef.value) {
        observer.observe(sentinelRef.value)
    }
})

onBeforeUnmount(() => {
    observer?.disconnect()
})

watch(() => props.sessionId, async () => {
    lastMessageId = 0
    hasMessages = true
    await loadMore()
}, { immediate: true })

defineExpose({
    scrollToBottom,
    smartScrollToBottom,
    resetAndLoad: loadMore
})
</script>
<template>
<div ref="scroll-ref" class="absolute inset-x-2 top-4 bottom-20 overflow-y-auto pr-1">
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
