<script setup lang="ts">
// Character: 角色卡片组件
// 2026-04 改动说明：
//   1. 新增 friend prop，支持从 Friend 快照字段读取数据（角色被删除后仍能展示）
//   2. 所有模板中的 character.xxx 替换为 displayCharacter.xxx，实现 character/friend 自动回退
//   3. 点击卡片后通过 Pinia store 初始化聊天状态，不再在组件内维护 friend/sessions/currentSessionId
import { computed, ref, useTemplateRef, nextTick } from 'vue';
import UpdateIcon from '@/components/character/icons/UpdateIcon.vue';
import { useUserStore } from '@/stores/user';
import { useChatStore } from '@/stores/chat';
import RemoveIcon from './icons/RemoveIcon.vue';
import api from '@/js/http/api';
import ChatField from '@/components/character/chat_field/ChatField.vue';
import { useRouter } from 'vue-router';

const props = defineProps(["character", "canEdit", "canRemoveFriend", "friendId", "friend"])
const emit = defineEmits(['remove'])
const router = useRouter()

const isHover = ref(false)
const user = useUserStore()
const chatStore = useChatStore()
const chatFieldRef = useTemplateRef('chat-field-ref')

// 统一展示数据源：优先使用实时 character，若角色被删除则回退到 friend 快照字段
const displayCharacter = computed(() => {
  const c = props.character
  const f = props.friend
  return {
    id: c?.id ?? null,
    name: c?.name || f?.character_name || '未知角色',
    photo: c?.photo || f?.character_photo || '',
    background_image: c?.background_image || f?.character_background_image || '',
    profile: c?.profile || f?.character_profile || '',
    author: c?.author || (f ? {
      user_id: f.author_id,
      username: f.author_username,
      photo: f.author_photo,
    } : null),
  }
})

async function handleRemoveCharacter() {
    try {
        const res = await api.post('/api/create/character/remove/', {
            character_id: props.character.id,
        })
        if(res.data.result === 'success') {
            emit('remove', props.character.id)
        }
    } catch(err) {
    }
}

async function handleRemoveFriend() {
    try {
        const res = await api.post('/api/friend/remove/', {
            friend_id: props.friendId
        })
        if(res.data.result === 'success') {
            emit('remove', props.friendId)
        }
    } catch(err) {

    }
}

async function openChatField() {
    if(!user.isLogin()) {
        await router.push({
            name: 'user-account-login-index'
        })
    } else {
        try {
            const res = await api.post('/api/friend/get_or_create/', {
                character_id: displayCharacter.value.id || props.character?.id
            })
            const data = res.data
            if(data.result === 'success') {
                chatStore.initFromGetOrCreate(data)
                await nextTick()
                chatFieldRef.value?.showModal()
            }
        } catch (err) {
        }
    }
}
</script>

<template>
    <div>
        <div class="avatar cursor-pointer" @mouseover="isHover = true" @mouseout="isHover = false" @click="openChatField">
            <div class="w-60 h-100 rounded-2xl relative">
                <img :src="displayCharacter.background_image" class="transition-transform duration-300" :class="{'scale-120': isHover}" alt="">
                <div class="absolute left-0 top-50 w-60 h-50 bg-linear-to-t from-black/40 to-transparent"></div>
                <div v-if="canEdit && displayCharacter.author?.user_id === user.id" class="absolute right-0 top-50">
                    <RouterLink @click.stop :to="{name: 'update-character', params: {character_id: displayCharacter.id}}" class="btn btn-circle btn-ghost bg-transparent">
                        <UpdateIcon />
                    </RouterLink>
                    <button @click.stop="handleRemoveCharacter" class="btn btn-circle btn-ghost bg-transparent">
                        <RemoveIcon />
                    </button>
                </div>
                <div v-if="canRemoveFriend" class="absolute top-50 right-0">
                    <button @click.stop="handleRemoveFriend" class="btn btn-circle btn-ghost bg-transparent">
                        <RemoveIcon />
                    </button>
                </div>
                <div class="absolute left-4 top-54 avatar ring-white">
                    <div class="w-16 rounded-full ring-3">
                        <img :src="displayCharacter.photo" alt="">
                    </div>
                </div>
                <div class="absolute left-24 right-4 top-58 text-white font-bold line-clamp-1 break-all">
                    {{ displayCharacter.name }}
                </div>
                <div class="absolute left-4 right-4 top-72 text-white line-clamp-4 break-all">
                    {{ displayCharacter.profile }}
                </div>
            </div>
        </div>
        <RouterLink v-if="displayCharacter.author?.user_id" :to="{name: 'user-space-index', params: {user_id: displayCharacter.author.user_id}}" class="flex items-center mt-4 gap-2 w-60">
            <div class="avatar">
                <div class="w-7 rounded-full">
                    <img :src="displayCharacter.author.photo" alt="">
                </div>
            </div>
            <div class="text-sm line-clamp-1 break-all">{{ displayCharacter.author.username }}</div>
        </RouterLink>
        <div v-else class="flex items-center mt-4 gap-2 w-60">
            <div class="avatar">
                <div class="w-7 rounded-full">
                    <img :src="displayCharacter.author?.photo || ''" alt="">
                </div>
            </div>
            <div class="text-sm line-clamp-1 break-all">{{ displayCharacter.author?.username || '未知作者' }}</div>
        </div>
        <ChatField ref="chat-field-ref" />
    </div>
</template>

<style scoped>

</style>