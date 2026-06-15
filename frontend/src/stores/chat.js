import { defineStore } from 'pinia'
import {
  conversationApi as defaultConversationApi,
  streamChat,
} from '../api/index.js'

let fallbackMessageIndex = 0

export function createChatStoreDefinition({
  id = 'chat',
  streamImpl = streamChat,
  conversationApi = defaultConversationApi,
} = {}) {
  let activeController = null
  let activeAssistantMessage = null

  return defineStore(id, {
    state: () => ({
      messages: [],
      conversations: [],
      conversationKbId: '',
      conversationId: '',
      streaming: false,
      error: null,
    }),

    actions: {
      async ask({ kbId, kb_id, question }) {
        const normalizedQuestion = normalizeQuestion(question)

        if (!normalizedQuestion) {
          const error = new Error('Question is required')
          this.error = error
          throw error
        }

        if (this.streaming) {
          const error = new Error('A chat response is already streaming')
          this.error = error
          throw error
        }

        const userMessage = createMessage({
          role: 'user',
          content: normalizedQuestion,
        })
        const assistantSeed = createMessage({
          role: 'assistant',
          content: '',
          sources: [],
          status: 'streaming',
        })

        this.messages.push(userMessage, assistantSeed)

        const assistantMessage = this.messages[this.messages.length - 1]
        const controller = new AbortController()
        activeController = controller
        activeAssistantMessage = assistantMessage
        this.streaming = true
        this.error = null

        try {
          await streamImpl(
            {
              kbId: kb_id ?? kbId,
              question: normalizedQuestion,
              conversationId: this.conversationId || undefined,
            },
            createStreamCallbacks({
              assistantMessage,
              controller,
              store: this,
            }),
            {
              signal: controller.signal,
            },
          )

          if (assistantMessage.status === 'streaming') {
            assistantMessage.status = 'done'
          }
        } catch (error) {
          if (controller.signal.aborted || isAbortError(error)) {
            if (assistantMessage.status === 'streaming') {
              assistantMessage.status = 'stopped'
            }
            return
          }

          assistantMessage.status = 'error'
          this.error = error
          throw error
        } finally {
          if (activeController === controller) {
            activeController = null
            activeAssistantMessage = null
            this.streaming = false
          }
        }
      },

      async loadConversations(kbId) {
        const normalizedKbId = normalizeText(kbId)

        if (!normalizedKbId) {
          this.conversations = []
          this.conversationKbId = ''
          return []
        }

        this.error = null

        try {
          const conversations = normalizeListResponse(
            await conversationApi.list(normalizedKbId),
          )
          this.conversations = conversations
          this.conversationKbId = normalizedKbId
          return conversations
        } catch (error) {
          this.error = error
          throw error
        }
      },

      async loadConversation(conversationId) {
        const normalizedConversationId = normalizeText(conversationId)

        if (!normalizedConversationId) {
          const error = new Error('Conversation id is required')
          this.error = error
          throw error
        }

        this.error = null
        this.stop()

        try {
          const storedMessages = normalizeListResponse(
            await conversationApi.getMessages(normalizedConversationId),
          )
          this.messages = storedMessages.map(mapStoredMessage)
          this.conversationId = normalizedConversationId
          return this.messages
        } catch (error) {
          this.error = error
          throw error
        }
      },

      async removeConversation(conversationId) {
        const normalizedConversationId = normalizeText(conversationId)

        if (!normalizedConversationId) {
          const error = new Error('Conversation id is required')
          this.error = error
          throw error
        }

        this.error = null

        try {
          await conversationApi.remove(normalizedConversationId)

          if (this.conversationId === normalizedConversationId) {
            this.reset()
          }

          if (this.conversationKbId) {
            await this.loadConversations(this.conversationKbId)
          } else {
            this.conversations = this.conversations.filter(
              (conversation) => conversation.id !== normalizedConversationId,
            )
          }
        } catch (error) {
          this.error = error
          throw error
        }
      },

      stop() {
        if (!activeController) {
          return
        }

        activeController.abort()

        if (activeAssistantMessage?.status === 'streaming') {
          activeAssistantMessage.status = 'stopped'
        }

        this.streaming = false
      },

      reset() {
        this.stop()
        this.messages = []
        this.conversationId = ''
        this.error = null
      },
    },
  })
}

export const useChatStore = createChatStoreDefinition()

function createStreamCallbacks({ assistantMessage, controller, store }) {
  return {
    onChunk(delta) {
      if (controller.signal.aborted) {
        return
      }

      assistantMessage.content += delta ?? ''
    },

    onSources(sources) {
      if (controller.signal.aborted) {
        return
      }

      assistantMessage.sources = Array.isArray(sources) ? sources : []
    },

    onDone(payload) {
      if (controller.signal.aborted) {
        return
      }

      const conversationId = payload?.conversation_id ?? payload?.conversationId

      if (conversationId) {
        store.conversationId = conversationId
      }

      assistantMessage.status = 'done'
    },
  }
}

function createMessage({ role, content, sources, status }) {
  return {
    id: createMessageId(),
    role,
    content,
    ...(sources ? { sources } : {}),
    ...(status ? { status } : {}),
  }
}

function mapStoredMessage(message) {
  const mapped = {
    id: message.id ?? createMessageId(),
    role: message.role,
    content: message.content ?? '',
  }

  if (message.role === 'assistant') {
    mapped.sources = Array.isArray(message.sources?.sources)
      ? message.sources.sources
      : []
    mapped.status = 'done'
  }

  return mapped
}

function createMessageId() {
  const randomId = globalThis.crypto?.randomUUID?.()

  if (randomId) {
    return `msg_${randomId}`
  }

  fallbackMessageIndex += 1
  return `msg_${Date.now()}_${fallbackMessageIndex}`
}

function normalizeQuestion(question) {
  return normalizeText(question)
}

function normalizeText(value) {
  return String(value ?? '').trim()
}

function normalizeListResponse(response) {
  if (Array.isArray(response)) {
    return response
  }

  if (Array.isArray(response?.items)) {
    return response.items
  }

  return []
}

function isAbortError(error) {
  return error?.name === 'AbortError'
}
