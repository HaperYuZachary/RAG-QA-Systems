import { defineStore } from 'pinia'
import { streamChat } from '../api/index.js'

let fallbackMessageIndex = 0

export function createChatStoreDefinition({
  id = 'chat',
  streamImpl = streamChat,
} = {}) {
  let activeController = null
  let activeAssistantMessage = null

  return defineStore(id, {
    state: () => ({
      messages: [],
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

function createMessageId() {
  const randomId = globalThis.crypto?.randomUUID?.()

  if (randomId) {
    return `msg_${randomId}`
  }

  fallbackMessageIndex += 1
  return `msg_${Date.now()}_${fallbackMessageIndex}`
}

function normalizeQuestion(question) {
  return String(question ?? '').trim()
}

function isAbortError(error) {
  return error?.name === 'AbortError'
}
