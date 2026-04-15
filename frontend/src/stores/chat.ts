import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/js/http/api'
import { useAudioStore } from './audio'

// Chat 全局状态管理（Pinia）
// 将会话状态从 ChatField 组件中抽离，避免多层 props 传递和重复 computed
// 核心设计：懒创建会话 —— 打开页面时若 currentSessionId 为 null，前端只渲染虚拟开场白，
// 等用户发送第一条消息时才真正调用后端创建 Session
export const useChatStore = defineStore('chat', () => {
  const friend = ref<any>(null)            // 当前聊天对象（含角色快照）
  const sessions = ref<any[]>([])          // 侧边栏历史会话列表
  const currentSessionId = ref<number | null>(null)  // null 表示处于虚拟新对话
  const history = ref<any[]>([])           // 当前聊天区的消息列表
  const isOpen = ref(false)                // 弹窗是否打开
  const isSidebarOpen = ref(true)          // 左侧会话列表是否展开
  const hasPlayedOpening = ref(false)      // 开场白语音是否已播放
  const isCreatingSession = ref(false)     // 防止并发创建 Session

  // 音频播放器已抽象到 useAudioStore，这里只负责在合适的时机调用 stop()
  const audioStore = useAudioStore()

  // 虚拟会话：当还没有真实 sessionId 时，前端自行渲染开场白，不入库
  const isVirtualSession = computed(() => !currentSessionId.value)

  // 以下 computed 均做快照回退：角色被删除后仍能从 friend 快照字段读取
  const characterName = computed(() => {
    return friend.value?.character_name || friend.value?.character?.name || '未知角色'
  })

  const characterPhoto = computed(() => {
    return friend.value?.character_photo || friend.value?.character?.photo || ''
  })

  const characterBackground = computed(() => {
    return friend.value?.character_background_image || friend.value?.character?.background_image || ''
  })

  const displayCharacter = computed(() => ({
    name: characterName.value,
    photo: characterPhoto.value,
  }))

  // 角色被删除（friend.character.id 为 null）后禁止聊天，只能查看历史
  const canChat = computed(() => {
    return !!friend.value?.character?.id
  })

  // 初始化：从 get_or_create 接口数据填充状态
  function initFromGetOrCreate(data: any) {
    friend.value = data.friend
    sessions.value = data.sessions || []
    currentSessionId.value = data.current_session_id
    history.value = []
    hasPlayedOpening.value = false
    audioStore.stop()
  }

  // 打开弹窗：若当前是虚拟新对话，直接在前端渲染开场白（不调用后端 get_history）
  function showModal() {
    isOpen.value = true
    if (!currentSessionId.value) {
      if (friend.value?.character_opening_message) {
        history.value = [{ role: 'ai', content: friend.value.character_opening_message, id: crypto.randomUUID() }]
      }
    }
  }

  function closeModal() {
    audioStore.stop()
    isOpen.value = false
  }

  // 删除所有真实 Session 后，回到虚拟状态并重新显示前端开场白
  function enterVirtualSession() {
    currentSessionId.value = null
    history.value = []
    hasPlayedOpening.value = false
    audioStore.stop()
    if (friend.value?.character_opening_message) {
      history.value = [{ role: 'ai', content: friend.value.character_opening_message, id: crypto.randomUUID() }]
    }
  }

  // 切换会话：清空当前历史，停止音频，外部需再调用 ChatHistory.resetAndLoad()
  async function switchSession(sessionId: number) {
    if (sessionId === currentSessionId.value) return
    currentSessionId.value = sessionId
    history.value = []
    hasPlayedOpening.value = false
    audioStore.stop()
  }

  // 手动新建真实 Session（点击 + 按钮）
  // 已在虚拟状态时直接返回，避免重复创建空会话
  async function createSession() {
    if (!friend.value?.id) return
    if (isVirtualSession.value) return
    if (isCreatingSession.value) return
    isCreatingSession.value = true
    try {
      const res = await api.post('/api/friend/session/create/', {
        friend_id: friend.value.id
      })
      if (res.data.result === 'success') {
        sessions.value.unshift(res.data.session)
        await switchSession(res.data.session.id)
      }
    } finally {
      isCreatingSession.value = false
    }
  }

  // 删除指定 Session；若删的是当前会话且无其他会话，则回到虚拟状态
  async function deleteSession(sessionId: number) {
    if (!confirm('确定删除该会话吗？')) return
    try {
      const res = await api.post('/api/friend/session/delete/', {
        session_id: sessionId
      })
      if (res.data.result === 'success') {
        sessions.value = sessions.value.filter((s: any) => s.id !== sessionId)
        if (sessionId === currentSessionId.value) {
          const next = sessions.value[0]
          if (next) {
            await switchSession(next.id)
          } else {
            enterVirtualSession()
          }
        }
      }
    } catch (err) {}
  }

  // 消息操作：供 ChatHistory / InputField 调用
  function handlePushBackMessage(msg: any) {
    history.value.push(msg)
  }

  function handlePushFrontMessage(msg: any) {
    history.value.unshift(msg)
  }

  function handleAddToLastMessage(delta: string) {
    const last = history.value[history.value.length - 1]
    if (last) last.content += delta
  }

  // InputField 在虚拟状态下发送第一条消息时，先创建 Session 再回调此处
  // 需要清除前端的虚拟开场白，避免和之后 ChatHistory 加载的真实历史重复
  function handleSessionCreated(session: any) {
    sessions.value.unshift(session)
    currentSessionId.value = session.id
    if (history.value.length === 1 && history.value[0].role === 'ai') {
      history.value = []
    }
  }

  return {
    friend,
    sessions,
    currentSessionId,
    history,
    isOpen,
    isSidebarOpen,
    hasPlayedOpening,
    isVirtualSession,
    characterName,
    characterPhoto,
    characterBackground,
    displayCharacter,
    canChat,
    initFromGetOrCreate,
    showModal,
    closeModal,
    enterVirtualSession,
    switchSession,
    createSession,
    deleteSession,
    handlePushBackMessage,
    handlePushFrontMessage,
    handleAddToLastMessage,
    handleSessionCreated,
  }
})
