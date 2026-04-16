<script setup lang="ts">
/**
 * Character: 角色卡片组件
 *
 * 2026-04 改动说明：
 *   1. 新增 friend prop，支持从 Friend 快照字段读取数据。
 *      当角色被删除后，Character 对象可能为 null，但 Friend 表中的快照字段
 *      （character_name / character_photo / character_opening_message 等）仍然保留，
 *      保证用户的历史记录页面和聊天弹窗都能正常展示。
 *   2. 所有模板中的 character.xxx 替换为 displayCharacter.xxx，实现 character / friend 自动回退。
 *   3. 点击卡片后通过 Pinia store 初始化聊天状态，不再在组件内维护 friend/sessions/currentSessionId。
 *   4. 引入 isChatActive 局部状态控制 ChatField 的渲染：
 *      - 只有当前被点击的卡片才会创建 ChatField 实例，
 *        避免 FriendIndex / Homepage 中多个卡片同时挂载 ChatField，
 *        导致每个 ChatHistory 的 onMounted 都触发 loadMore 的 bug。
 *      - 关闭弹窗时（chatStore.isOpen 变为 false），watch 自动把 isChatActive 清为 false，
 *        销毁本卡片的 ChatField DOM 和内部音频资源。
 */
import { computed, ref, useTemplateRef, nextTick, watch } from 'vue';
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

// ==================== ChatField 生命周期控制 ====================

/**
 * isChatActive 是本组件的局部变量，与全局 chatStore.isOpen 解耦。
 * 原因：FriendIndex 会同时渲染 N 个 Character，如果每个内部都写
 *      <ChatField v-if="chatStore.isOpen">，则点击任意一张卡片时
 *      所有卡片的 ChatField 都会同时挂载，导致 N 次 loadMore。
 *
 * 现在：
 *   - 点击卡片 -> isChatActive = true -> 只有当前卡片创建 ChatField
 *   - 关闭弹窗 -> isOpen = false -> watch 触发 -> isChatActive = false -> 销毁实例
 */
const isChatActive = ref(false)

watch(() => chatStore.isOpen, (val) => {
  if (!val) isChatActive.value = false
})

// ==================== 展示数据源 ====================

/**
 * displayCharacter 提供统一的数据视图：
 *   优先使用实时 character 对象；若角色被删除（character 为 null），
 *   则回退到 friend 快照字段；若两者皆无，则使用兜底默认值。
 */
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

// ==================== 事件处理 ====================

async function handleRemoveCharacter() {
  try {
    const res = await api.post('/api/create/character/remove/', {
      character_id: props.character.id,
    })
    if (res.data.result === 'success') {
      emit('remove', props.character.id)
    }
  } catch(err) {}
}

async function handleRemoveFriend() {
  try {
    const res = await api.post('/api/friend/remove/', {
      friend_id: props.friendId
    })
    if (res.data.result === 'success') {
      emit('remove', props.friendId)
    }
  } catch(err) {}
}

/**
 * 打开聊天弹窗的主入口：
 *   1. 未登录 -> 跳转登录页
 *   2. 已登录 -> 调 /api/friend/get_or_create/ 获取或创建 Friend 记录
 *   3. 用返回数据初始化 chatStore
 *   4. 置 isChatActive = true，渲染 ChatField
 *   5. nextTick 后调用 ChatField.showModal() 真正打开弹窗
 */
async function openChatField() {
  if (!user.isLogin()) {
    await router.push({
      name: 'user-account-login-index'
    })
  } else {
    try {
      const res = await api.post('/api/friend/get_or_create/', {
        character_id: displayCharacter.value.id || props.character?.id
      })
      const data = res.data
      if (data.result === 'success') {
        chatStore.initFromGetOrCreate(data)
        isChatActive.value = true
        await nextTick()
        chatFieldRef.value?.showModal()
      }
    } catch (err) {}
  }
}
</script>

<template>
  <div>
    <!-- 卡片主体 -->
    <div class="avatar cursor-pointer" @mouseover="isHover = true" @mouseout="isHover = false" @click="openChatField">
      <div class="w-60 h-100 rounded-2xl relative">
        <img :src="displayCharacter.background_image" class="transition-transform duration-300" :class="{'scale-120': isHover}" alt="">
        <div class="absolute left-0 top-50 w-60 h-50 bg-linear-to-t from-black/40 to-transparent"></div>
        <!-- 编辑/删除按钮（仅作者可见） -->
        <div v-if="canEdit && displayCharacter.author?.user_id === user.id" class="absolute right-0 top-50">
          <RouterLink @click.stop :to="{name: 'update-character', params: {character_id: displayCharacter.id}}" class="btn btn-circle btn-ghost bg-transparent">
            <UpdateIcon />
          </RouterLink>
          <button @click.stop="handleRemoveCharacter" class="btn btn-circle btn-ghost bg-transparent">
            <RemoveIcon />
          </button>
        </div>
        <!-- 移除朋友按钮 -->
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

    <!-- 作者信息 -->
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

    <!-- 只有当前激活的卡片才渲染 ChatField -->
    <ChatField v-if="isChatActive" ref="chat-field-ref" />
  </div>
</template>

<style scoped>
</style>
