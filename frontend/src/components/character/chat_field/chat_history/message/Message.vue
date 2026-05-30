<script setup lang="ts">
import { useUserStore } from '@/stores/user';

const props = defineProps(['message', 'character'])

const user = useUserStore()
</script>
<template>
    <div>
        <div v-if="message.role === 'ai' && message.content" class="chat chat-start">
            <div class="chat-image avatar">
                <div class="w-10 rounded-full">
                    <img :src="character.photo" alt="">
                </div>
            </div>
            <div class="chat-bubble whitespace-pre-wrap break-all">{{ message.content }}</div>
        </div>
        <div v-else-if="message.role === 'user' && (message.content || message.images?.length)" class="chat chat-end">
            <div class="chat-image avatar">
                <div class="w-10 rounded-full">
                    <img :src="user.photo" alt="">
                </div>
            </div>
            <div class="flex flex-col items-end gap-2">
                <!-- 图片列表 -->
                <div v-if="message.images?.length" class="flex gap-2 flex-wrap justify-end">
                    <img
                        v-for="(src, i) in message.images"
                        :key="i"
                        :src="src"
                        class="w-24 h-24 object-cover rounded-xl shadow-md"
                    />
                </div>
                <div v-if="message.content" class="chat-bubble chat-bubble-success whitespace-pre-wrap break-all">{{ message.content }}</div>
            </div>
        </div>
    </div>
</template>
<style scoped>
</style>
