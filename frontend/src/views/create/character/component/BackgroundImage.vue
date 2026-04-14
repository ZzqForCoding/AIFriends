<script setup lang="ts">
import {computed, nextTick, onBeforeUnmount, ref, useTemplateRef, watch} from "vue";
import CameraIcon from "@/views/user/profile/component/icon/CameraIcon.vue";
import Croppie from "croppie";

const props = defineProps(['backgroundImage'])
const myBackgroundImage = ref(props.backgroundImage)
const fileInputRef = useTemplateRef<HTMLInputElement>('file-input-ref')
const modalRef = useTemplateRef<HTMLDialogElement>('modal-ref')
const croppieRef = useTemplateRef<HTMLDivElement>('croppie-ref')
let croppie: Croppie | null = null

const previewStyle = computed(() => ({
  aspectRatio: `${window.innerWidth} / ${window.innerHeight}`
}))

function onFileChange(e: any) {
  const file = e.target.files[0]
  e.target.value = ''
  if(!file) return

  const reader = new FileReader()
  reader.onload = () => {
    openModal(reader.result)
  }
  reader.readAsDataURL(file)
}

async function openModal(photo: any) {
  modalRef.value?.showModal()
  if (!croppieRef.value) return
  await nextTick()
  if(!croppie) {
    const modalBox = modalRef.value?.querySelector('.modal-box') as HTMLElement | null
    const availableWidth = modalBox ? modalBox.clientWidth - 48 : Math.min(576, window.innerWidth - 48)
    const availableHeight = Math.min(480, window.innerHeight - 220)
    const ratio = window.innerWidth / window.innerHeight

    let viewportWidth = availableWidth
    let viewportHeight = viewportWidth / ratio

    if (viewportHeight > availableHeight) {
      viewportHeight = availableHeight
      viewportWidth = viewportHeight * ratio
    }

    viewportWidth = Math.floor(viewportWidth)
    viewportHeight = Math.floor(viewportHeight)

    croppie = new Croppie(croppieRef.value, {
      viewport: {
        width: viewportWidth,
        height: viewportHeight,
        type: 'square'
      },
      boundary: {width: availableWidth, height: availableHeight},
      enableOrientation: true,
      enforceBoundary: true
    })
    await croppie.bind({ url: photo })
  }
}

async function crop() {
  if(!croppie) return
  myBackgroundImage.value = await croppie.result({
    type: 'base64',
    size: 'original'
  })

  modalRef.value?.close()
}

onBeforeUnmount(() => {
  croppie?.destroy()
})

watch(()=> props.backgroundImage, newVal=> {
  myBackgroundImage.value = newVal
})

defineExpose({
  myBackgroundImage,
})
</script>

<template>
  <fieldset class="fieldset">
    <label class="label text-base">聊天背景</label>
    <div class="avatar relative">
      <div v-if="myBackgroundImage" class="w-24 rounded-box overflow-hidden" :style="previewStyle">
        <img :src="myBackgroundImage" class="w-full h-full object-cover" alt="">
      </div>
      <div v-else class="w-24 rounded-box bg-base-200" :style="previewStyle"/>
      <div @click="fileInputRef?.click()" class="w-24 rounded-box absolute left-0 top-0 bg-black/20 flex justify-center items-center cursor-pointer" :style="previewStyle">
        <CameraIcon/>
      </div>
    </div>
  </fieldset>

  <input ref="file-input-ref" type="file" class="hidden" accept="image/*" @change="onFileChange">
  <dialog ref="modal-ref" class="modal">
    <div class="modal-box transition-none max-w-2xl">
      <button @click="modalRef?.close()" class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">x</button>
      <div ref="croppie-ref" class="flex flex-col my-4" />
      <div class="modal-action">
        <button @click="modalRef?.close()" class="btn">取消</button>
        <button @click="crop" class="btn btn-neutral">确定</button>
      </div>
    </div>
  </dialog>
</template>

<style scoped>

</style>