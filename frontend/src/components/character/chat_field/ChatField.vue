<script setup lang="ts">
import { computed, useTemplateRef } from 'vue';
import InputField from './input_field/InputField.vue';
import CharacterPhotoField from './character_photo_field/CharacterPhotoField.vue';

const props = defineProps(['friend'])

const modalRef = useTemplateRef<HTMLDialogElement>('modal-ref')

const modalStyle = computed(() => {
  if (props.friend) {
    return {
      backgroundImage: `url(${props.friend.character.background_image})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat',
    }
  } else {
    return {}
  }
})

function showModal() {
    modalRef.value?.showModal()
}

defineExpose({
    showModal
})
</script>
<template>
    <dialog ref="modal-ref" class="modal">
        <div class="modal-box w-90 h-150" :style="modalStyle">
            <button @click="modalRef?.close()" class="btn btn-circle btn-sm btn-ghost bg-transparent absolute right-2 top-2">x</button>
            <InputField />
            <CharacterPhotoField v-if="friend" :character="friend.character" />
        </div>
    </dialog>
</template>
<style scoped>

</style>
