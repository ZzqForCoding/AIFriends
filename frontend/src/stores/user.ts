import {defineStore} from "pinia";
import {ref} from "vue";

export const useUserStore = defineStore('user', ()=> {
    const id = ref(0)
    const username = ref('')
    const photo = ref('')
    const profile = ref('')
    const accessToken = ref('')
    const hasPulledUserInfo = ref(false)

    function isLogin() : boolean {
        return !!accessToken.value
    }

    function setAccessToken(token:string):void {
        accessToken.value = token
    }

    function setUserInfo(data:any) {
        id.value = data.user_id
        username.value = data.username
        photo.value = data.photo
        profile.value = data.profile
    }

    function logout() {
        id.value = 0
        username.value = ''
        photo.value = ''
        profile.value = ''
        accessToken.value = ''
    }

    function setHasPulledUserInfo(newStatus: any) {
        hasPulledUserInfo.value = newStatus
    }

    return {
        id,
        username,
        photo,
        profile,
        accessToken,
        hasPulledUserInfo,
        isLogin,
        setAccessToken,
        setUserInfo,
        logout,
        setHasPulledUserInfo
    }
})