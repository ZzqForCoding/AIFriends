<script setup lang="ts">
import { nextTick, ref, useTemplateRef, watch } from 'vue';
import Message from './message/Message.vue';
import api from '@/js/http/api';
import InfiniteScroll from '@/components/common/InfiniteScroll.vue';

const props = defineProps(['history', 'sessionId', 'character'])
const emit = defineEmits(['pushFrontMessage'])
const infiniteScrollRef = useTemplateRef<InstanceType<typeof InfiniteScroll>>('infinite-scroll-ref')
let isLoading = false
let hasMessages = true
let lastMessageId = 0

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
            const container = infiniteScrollRef.value?.container
            const oldHeight = container?.scrollHeight
            const oldTop = container?.scrollTop
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
            const newHeight = container?.scrollHeight
            const el = container
            if(el) {
                el.scrollTop = oldTop! + newHeight! - oldHeight!
            }

            if(infiniteScrollRef.value?.checkSentinelVisible()) {
                await loadMore()
            }
        }
    }
}

async function scrollToBottom() {
    await nextTick()
    infiniteScrollRef.value?.scrollToBottom()
}

async function smartScrollToBottom() {
    await nextTick()
    infiniteScrollRef.value?.smartScrollToBottom()
}

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
<InfiniteScroll
  ref="infinite-scroll-ref"
  class="absolute inset-x-2 top-4 bottom-14 pr-2"
  sentinel-position="top"
  :has-more="hasMessages"
  @load-more="loadMore"
>
    <!-- pb-8 为底部提示条（角色已删除）留出安全距离，避免最后一条消息被遮挡 -->
    <div class="pb-8">
        <Message
            v-for="message in history"
            :key="message.id"
            :message="message"
            :character="character"
        />
    </div>
</InfiniteScroll>
</template>
