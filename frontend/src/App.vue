<script setup lang="ts">
import NavBar from "@/components/navbar/NavBar.vue";
import {onMounted} from "vue";
import api from "@/js/http/api.ts";
import {useUserStore} from "@/stores/user.ts";
import {useRoute} from "vue-router";
import router from "@/router";
import axios from "axios";

const user = useUserStore()
const route = useRoute()

onMounted(async ()=> {
  // 主动刷新 token
  try {
    const res = await api.get('/api/user/account/get_user_info/')
    const data = res.data
    if(data.result === 'success') {
      user.setUserInfo(data)
    }
  } catch (e) {
  } finally {
    user.setHasPulledUserInfo(true)
    if(route.meta.needLogin && !user.isLogin()) {
      await router.replace({
        name: 'user-account-login-index'
      })
    }
  }
})
</script>

<template>
  <NavBar>
    <router-view />
  </NavBar>
</template>

<style scoped>
</style>
