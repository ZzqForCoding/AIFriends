import {defineStore} from "pinia";
import {ref} from "vue";

export const useUserStore = defineStore('user', ()=> {
    const id = ref(3)
    const username = ref('zzq')
    const photo = ref('http://127.0.0.1:8000/media/user/photos/1_b8714cbe54.png')
    const profile = ref('')
    const accessToken = ref('123')

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

    return {
        id,
        username,
        photo,
        profile,
        accessToken,
        isLogin,
        setAccessToken,
        setUserInfo,
        logout
    }
})