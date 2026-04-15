<script setup lang="ts">
import Character from '@/components/character/Character.vue';
import api from '@/js/http/api';
import { nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef } from 'vue';


const friends = ref<any[]>([])
const isLoading = ref(false)
const hasFriends = ref(true)
const sentinelRef= useTemplateRef<HTMLDivElement>('sentinel-ref')

function checkSentinelVisible() {  // 判断哨兵是否能被看到
  if (!sentinelRef.value) return false

  const rect = sentinelRef.value.getBoundingClientRect()
  return rect.top < window.innerHeight && rect.bottom > 0
}

function removeFriend(friendId: number) {
    friends.value = friends.value.filter(f => f.id !== friendId)
}

async function loadMore() {
    if(isLoading.value || !hasFriends.value) return
    isLoading.value = true

    let newFriends = []
    try {
        const res = await api.get('/api/friend/get_list/', {
            params: {
                items_count: friends.value.length
            }
        })
        const data = res.data
        if(data.result === 'success') {
            newFriends = data.friends
        }
    } catch (err) {
    } finally {
        isLoading.value = false
        if(newFriends.length === 0) {
            hasFriends.value = false
        } else {
            friends.value.push(...newFriends)
            await nextTick()
            
            if(checkSentinelVisible()) {
                await loadMore()
            }
        }
    }
}

let observer: IntersectionObserver | null = null
onMounted(async()=> {
    await loadMore()

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
    observer.observe(sentinelRef.value!)
})

onBeforeUnmount(() => {
    observer?.disconnect()
})
</script>

<template>
    <div class="flex flex-col items-center mb-12">
        <div class="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-9 mt-12 justify-items-center w-full px-9">
            <!-- 传入 friend 对象，使 Character 组件在 Character 被删除后仍能从快照字段展示信息 -->
            <Character
                v-for="friend in friends"
                :key="friend.id"
                :character="friend.character"
                :friend="friend"
                :canRemoveFriend="true"
                :friendId="friend.id"
                @remove="removeFriend"
            />
        </div>
        <div ref="sentinel-ref" class="h-2 mt-8"></div>
        <div v-if="isLoading" class="text-gray-500 mt-4">加载中...</div>
        <div v-else-if="!hasFriends" class="text-gray-500 mt-4">没有更多聊天了</div>
    </div>
</template>

<style scoped>

</style>