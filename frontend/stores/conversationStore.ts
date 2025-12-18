/**
 * Zustand store for conversation state management
 */

import { create } from 'zustand'
import type { Conversation, ConversationCreateRequest, MessageCreateRequest } from '@/types/conversation'

interface ConversationState {
  // State
  currentConversation: Conversation | null
  isLoading: boolean
  error: string | null

  // Actions
  startConversation: (message: string) => Promise<void>
  sendMessage: (message: string) => Promise<void>
  resetConversation: () => void
  clearError: () => void
}

// Get API URL from environment variable
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const useConversationStore = create<ConversationState>((set, get) => ({
  // Initial state
  currentConversation: null,
  isLoading: false,
  error: null,

  // Start a new conversation
  startConversation: async (message: string) => {
    set({ isLoading: true, error: null })

    try {
      const payload: ConversationCreateRequest = { initial_message: message }

      const response = await fetch(`${API_URL}/api/v1/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || 'Failed to start conversation')
      }

      const data: Conversation = await response.json()
      set({ currentConversation: data, isLoading: false })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred'
      set({ error: errorMessage, isLoading: false })
      console.error('Error starting conversation:', error)
    }
  },

  // Send a message in existing conversation
  sendMessage: async (message: string) => {
    const { currentConversation } = get()
    if (!currentConversation) {
      set({ error: 'No active conversation' })
      return
    }

    set({ isLoading: true, error: null })

    try {
      const payload: MessageCreateRequest = { content: message }

      const response = await fetch(
        `${API_URL}/api/v1/conversations/${currentConversation.id}/messages`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }
      )

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || 'Failed to send message')
      }

      const data: Conversation = await response.json()
      set({ currentConversation: data, isLoading: false })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred'
      set({ error: errorMessage, isLoading: false })
      console.error('Error sending message:', error)
    }
  },

  // Reset conversation (start fresh)
  resetConversation: () => {
    set({ currentConversation: null, error: null, isLoading: false })
  },

  // Clear error message
  clearError: () => {
    set({ error: null })
  },
}))
