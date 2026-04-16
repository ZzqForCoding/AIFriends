import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/js/http/api'
import { useAudioStore } from './audio'

/**
 * Chat 全局状态管理（Pinia）
 *
 * 2026-04 重构背景：
 *   之前 friend/sessions/history/currentSessionId 全部散落在 ChatField 组件内部，
 *   导致 Character -> ChatField -> ChatHistory -> InputField 之间 props 传递极深，
 *   且多个组件都要对同一份状态做 computed，逻辑耦合严重。
 *
 * 本 Store 把"会话状态"彻底抽离，核心解决两个问题：
 *   1. 懒创建会话（Lazy Session Creation）
 *      - 用户首次打开某角色聊天页时，若该角色下没有任何历史 Session，
 *        后端返回 current_session_id = null，前端进入"虚拟新对话"状态。
 *      - 此时只在前端渲染 character_opening_message，不调用后端创建真实 Session，
 *        等用户真正发送第一条消息时，InputField 再调 /api/friend/session/create/ 懒创建。
 *   2. 角色删除后的快照保护
 *      - Friend 表新增了 character_name / character_photo / character_opening_message 等快照字段。
 *      - 当 Character 被删除（SET_NULL），前端仍能从 friend 快照中读取信息，
 *        历史会话列表和消息记录都可以正常查看，只是不能再发送新消息。
 */
export const useChatStore = defineStore('chat', () => {
  // ==================== 核心状态 ====================
  const friend = ref<any>(null)            // 当前聊天的 Friend 对象（含角色快照）
  const sessions = ref<any[]>([])          // 左侧边栏：该 Friend 下的历史 Session 列表
  const currentSessionId = ref<number | null>(null)  // null = 虚拟新对话；有值 = 真实会话
  const history = ref<any[]>([])           // 当前聊天区渲染的消息数组
  const isOpen = ref(false)                // 聊天弹窗是否打开（控制 ChatField 显隐）
  const isSidebarOpen = ref(true)          // 左侧会话列表是否展开
  const hasPlayedOpening = ref(false)      // 开场白语音是否已播放过（预留）
  const isCreatingSession = ref(false)     // 防止用户快速双击导致并发创建 Session

  // 音频播放已抽象到 useAudioStore，本 Store 只负责在"切换/关闭/重置"时叫停音频
  const audioStore = useAudioStore()

  // ==================== 派生状态 ====================
  // 虚拟会话：currentSessionId 为 null 时，前端自行维护开场白，不入库
  const isVirtualSession = computed(() => !currentSessionId.value)

  // 以下 computed 均做"快照 -> 实时对象 -> 兜底默认值"的三级回退
  const characterName = computed(() => {
    return friend.value?.character_name || friend.value?.character?.name || '未知角色'
  })

  const characterPhoto = computed(() => {
    return friend.value?.character_photo || friend.value?.character?.photo || ''
  })

  const characterBackground = computed(() => {
    return friend.value?.character_background_image || friend.value?.character?.background_image || ''
  })

  // 只把聊天区真正需要的字段暴露出去，减少子组件对 Store 的直接依赖
  const displayCharacter = computed(() => ({
    name: characterName.value,
    photo: characterPhoto.value,
  }))

  // 角色被删除后（friend.character.id 为 null），禁止继续聊天，只能只读历史
  const canChat = computed(() => {
    return !!friend.value?.character?.id
  })

  // ==================== 动作（Actions） ====================

  /**
   * 初始化：点击角色卡片后，从 /api/friend/get_or_create/ 的返回数据填充 Store
   * 注意：此时不设置 isOpen，isOpen 的打开由 ChatField.showModal() 负责
   */
  function initFromGetOrCreate(data: any) {
    friend.value = data.friend
    sessions.value = []
    currentSessionId.value = data.current_session_id
    history.value = []
    hasPlayedOpening.value = false
    audioStore.stop()
  }

  /**
   * 打开弹窗
   * 若当前是虚拟新对话（currentSessionId === null），直接在前端插入开场白消息，
   * 不调用后端 get_history；若已有真实 Session，则由 ChatField 负责调用 resetAndLoad()
   */
  function showModal() {
    isOpen.value = true
    if (!currentSessionId.value) {
      if (friend.value?.character_opening_message) {
        history.value = [{
          role: 'ai',
          content: friend.value.character_opening_message,
          id: crypto.randomUUID()
        }]
      }
    }
  }

  function closeModal() {
    audioStore.stop()
    isOpen.value = false
  }

  /**
   * 进入虚拟新对话状态
   * 使用场景：删除最后一个真实 Session 后，需要回到"新的对话"状态
   */
  function enterVirtualSession() {
    currentSessionId.value = null
    history.value = []
    hasPlayedOpening.value = false
    audioStore.stop()
    if (friend.value?.character_opening_message) {
      history.value = [{
        role: 'ai',
        content: friend.value.character_opening_message,
        id: crypto.randomUUID()
      }]
    }
  }

  /**
   * 切换会话
   * 只负责"改 currentSessionId + 清空 history"，不加载历史。
   * 外部（ChatField）需要在 nextTick 后再调用 ChatHistory.resetAndLoad() 加载消息，
   * 保证 DOM 更新完成、sessionId props 已同步到 ChatHistory 后再发请求。
   */
  async function switchSession(sessionId: number) {
    if (sessionId === currentSessionId.value) return
    currentSessionId.value = sessionId
    history.value = []
    hasPlayedOpening.value = false
    audioStore.stop()
  }

  /**
   * 手动新建真实 Session（用户点击侧边栏 + 按钮）
   * 若当前已经在虚拟新对话状态，则直接返回，避免创建空 Session。
   */
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

  /**
   * 删除指定 Session
   * 若删除的是当前正在显示的会话，则自动切到 sessions[0]（最新会话）；
   * 如果删完后没有剩余会话了，回到虚拟新对话状态。
   */
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

  // ==================== 消息操作（供 ChatHistory / InputField 调用） ====================

  /** 在消息列表末尾追加一条消息（用户发送新消息 / AI 开场占位消息） */
  function handlePushBackMessage(msg: any) {
    history.value.push(msg)
  }

  /** 在消息列表头部插入一条消息（加载历史时，旧消息 prepend 到顶部） */
  function handlePushFrontMessage(msg: any) {
    history.value.unshift(msg)
  }

  /** 追加内容到当前最后一条消息（流式 AI 回复时逐字追加） */
  function handleAddToLastMessage(delta: string) {
    const last = history.value[history.value.length - 1]
    if (last) last.content += delta
  }

  /**
   * InputField 在虚拟状态下发送第一条消息时，先创建 Session 再回调此处
   * 需要把 sessions 重置为只有新 Session 一个，并清空前端虚拟开场白，
   * 避免之后 ChatHistory 加载真实历史时开场白重复出现。
   */
  function handleSessionCreated(session: any) {
    sessions.value = [session]
    currentSessionId.value = session.id
    history.value = []
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
