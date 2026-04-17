const platform: string = 'vue'  // vue, django, cloud

const CONFIG_API = {
    HTTP_URL: '',
    VAD_URL: ''
}

if (platform === 'vue') {
    CONFIG_API.HTTP_URL = 'http://127.0.0.1:8000/'
    CONFIG_API.VAD_URL = 'http://localhost:5173/vad/'
} else if(platform === 'django') {
    CONFIG_API.HTTP_URL = 'http://127.0.0.1:8000/'
    CONFIG_API.VAD_URL = 'http://127.0.0.1:8000/static/frontend/vad/'
} else if(platform === 'cloud') {
    CONFIG_API.HTTP_URL = 'https://aichat.zzqahm.top/'
    CONFIG_API.VAD_URL = 'https://aichat.zzqahm.top/static/frontend/vad/'
}

export default CONFIG_API