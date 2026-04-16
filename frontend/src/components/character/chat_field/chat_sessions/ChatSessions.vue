<script setup lang="ts">
/**
 * ChatSessions: 聊天侧边栏会话列表
 *
 * 职责：
 *   - 展示"新的对话"（虚拟会话）与真实历史会话列表
 *   - 提供新建、切换、删除会话的 UI 入口
 *   - 所有状态读取自 useChatStore，动作通过 emit 交给父组件 ChatField 执行，
 *     因为切换/创建/删除会话后，父组件需要协调 ChatHistory 的 resetAndLoad()
 */
import api from '@/js/http/api';
import { useChatStore } from '@/stores/chat'
import { nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef } from 'vue';

const emit = defineEmits<{
  'close-sidebar': []
  'create-session': []
  'switch-session': [sessionId: number]
  'delete-session': [sessionId: number]
}>()

const chatStore = useChatStore()
const isLoading = ref(false)
const hasSessions = ref(true)
const sentinelRef = useTemplateRef('sentinel-ref')

const containerRef = useTemplateRef<HTMLDivElement>('container-ref')

function checkSentinelVisible() {
    if(!sentinelRef.value || !containerRef.value) return false
    const sentinelRect = sentinelRef.value.getBoundingClientRect()
    const containerRect = containerRef.value.getBoundingClientRect()
    return sentinelRect.top < containerRect.bottom && sentinelRect.bottom > containerRect.top
}

async function loadMore() {
    if(isLoading.value || !hasSessions.value) return
    if(!chatStore.friend?.id) return
    isLoading.value = true

    let newSessions: any[] = []
    try {
        const itemsCount = chatStore.sessions.length
        const res = await api.get('/api/friend/session/get_list/', {
            params: {
                friend_id: chatStore.friend.id,
                items_count: itemsCount
            }
        })
        const data = res.data
        if(data.result === 'success') {
            newSessions = data.sessions
        }
    } catch(err) {
    } finally {
        isLoading.value = false
        if(newSessions.length === 0) {
            hasSessions.value = false
        } else {
            chatStore.sessions.push(...newSessions)
            await nextTick()
            if(checkSentinelVisible()) {
                await loadMore()
            }
        }
    }
}

let observer: IntersectionObserver | null = null
onMounted(async() => {
    await loadMore()
    observer = new IntersectionObserver(
        entries => {
            entries.forEach(entry => {
                if(entry.isIntersecting) {
                    loadMore()
                }
            })
        },
        {root: containerRef.value, rootMargin: '2px', threshold: 0}
    )
    if (sentinelRef.value) {
        observer.observe(sentinelRef.value)
    }
})

onBeforeUnmount(() => {
    observer?.disconnect()
})

</script>

<template>
  <!-- 侧边栏头部 -->
  <div class="h-16 flex items-center justify-between px-4 border-b border-base-300 shrink-0">
    <span class="font-bold">历史对话</span>
    <div class="flex items-center gap-1">
      <!-- 角色被删除后（canChat=false）或虚拟会话时不允许新建 -->
      <button
        v-if="chatStore.canChat && !chatStore.isVirtualSession"
        class="btn btn-ghost btn-sm btn-circle"
        @click="emit('create-session')"
        title="新建对话"
      >+</button>
      <button class="btn btn-ghost btn-sm btn-circle" @click="emit('close-sidebar')" title="收起侧边栏">←</button>
    </div>
  </div>

  <!-- 会话列表 -->
  <div ref="container-ref" class="flex-1 overflow-y-auto p-2 space-y-1">
    <!-- 虚拟会话：始终显示在最上方，表示"新的对话" -->
    <div
      v-if="chatStore.isVirtualSession"
      class="p-2 rounded-lg cursor-pointer transition-colors flex items-center justify-between bg-primary text-primary-content font-medium"
    >
      <span class="truncate">新的对话</span>
    </div>

    <!-- 真实历史会话列表 -->
    <div
      v-for="session in chatStore.sessions"
      :key="session.id"
      class="p-2 rounded-lg cursor-pointer transition-colors flex items-center justify-between group"
      :class="session.id === chatStore.currentSessionId ? 'bg-primary text-primary-content font-medium' : 'bg-base-100 hover:bg-base-300'"
      @click="emit('switch-session', session.id)"
    >
      <span class="truncate">{{ session.session_name }}</span>
      <button
        class="btn btn-ghost btn-xs btn-circle opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-1"
        :class="session.id === chatStore.currentSessionId ? 'text-white/80 hover:text-white hover:bg-white/20' : 'text-base-content hover:bg-base-300'"
        @click.stop="emit('delete-session', session.id)"
        title="删除"
      >×</button>
    </div>
    <div ref="sentinel-ref" class="mt-8 h-2 bg-red-500"></div>
    <div v-if="isLoading" class="text-gray-500 mt-4">加载中</div>
    <div v-else-if="!hasSessions" class="text-gray-500 mt-4">没有更多会话了...</div>
  </div>
</template>

<style scoped>
</style>
