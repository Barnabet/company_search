/**
 * Zustand store for conversation state management
 *
 * Stateless architecture - messages are managed locally,
 * backend processes the full history on each request.
 */

import { create } from 'zustand'
import type { ExtractionResult } from '@/types/conversation'

// ============================================================================
// Types
// ============================================================================

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

interface ActivityMatch {
  activity: string
  naf_codes: string[]
  score: number
  selected: boolean
}

interface ChatResponse {
  message: string
  extraction_result: ExtractionResult | null
  company_count: number | null
  count_semantic: number | null
  naf_codes: string[] | null
  api_result: Record<string, unknown> | null
  activity_matches: ActivityMatch[] | null
}

interface ConversationState {
  // State
  messages: ChatMessage[]
  extraction: ExtractionResult | null
  companyCount: number | null
  countSemantic: number | null
  nafCodes: string[] | null
  apiResult: Record<string, unknown> | null
  activityMatches: ActivityMatch[] | null
  isLoading: boolean
  isUpdatingSelection: boolean
  error: string | null

  // Actions
  sendMessage: (content: string) => Promise<void>
  updateActivitySelection: (index: number) => Promise<void>
  resetConversation: () => void
  clearError: () => void
}

export type { ActivityMatch }

// Get API URL from environment variable
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ============================================================================
// Store
// ============================================================================

export const useConversationStore = create<ConversationState>((set, get) => ({
  // Initial state
  messages: [],
  extraction: null,
  companyCount: null,
  countSemantic: null,
  nafCodes: null,
  apiResult: null,
  activityMatches: null,
  isLoading: false,
  isUpdatingSelection: false,
  error: null,

  // Send a message (works for both first message and follow-ups)
  sendMessage: async (content: string) => {
    const { messages } = get()

    // Create user message
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }

    // Optimistic update: show user message immediately
    set({
      messages: [...messages, userMessage],
      isLoading: true,
      error: null,
    })

    try {
      // Build message history for API
      const messageHistory = [...messages, userMessage].map(m => ({
        role: m.role,
        content: m.content,
      }))

      // Get current extraction and activity matches for caching
      const { extraction, activityMatches } = get()

      const response = await fetch(`${API_URL}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: messageHistory,
          previous_extraction: extraction,
          previous_activity_matches: activityMatches,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || 'Failed to send message')
      }

      const data: ChatResponse = await response.json()

      // Create assistant message
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now()}-assistant`,
        role: 'assistant',
        content: data.message,
        created_at: new Date().toISOString(),
      }

      // Update state with response
      // Only update extraction/counts if we got new data (don't reset on rejection)
      const currentState = get()
      set({
        messages: [...currentState.messages, assistantMessage],
        extraction: data.extraction_result ?? currentState.extraction,
        companyCount: data.company_count ?? currentState.companyCount,
        countSemantic: data.count_semantic ?? currentState.countSemantic,
        nafCodes: data.naf_codes ?? currentState.nafCodes,
        apiResult: data.api_result ?? currentState.apiResult,
        activityMatches: data.activity_matches ?? currentState.activityMatches,
        isLoading: false,
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred'
      set({ error: errorMessage, isLoading: false })
      console.error('Error sending message:', error)
    }
  },

  // Update activity selection and re-run search
  updateActivitySelection: async (index: number) => {
    const { activityMatches, extraction } = get()

    if (!activityMatches || !extraction) return

    // Toggle selection for the clicked activity
    const updatedMatches = activityMatches.map((match, i) => ({
      ...match,
      selected: i === index ? !match.selected : match.selected
    }))

    // Optimistic update
    set({ activityMatches: updatedMatches, isUpdatingSelection: true, error: null })

    try {
      const response = await fetch(`${API_URL}/api/v1/update-selection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          extraction_result: extraction,
          activity_matches: updatedMatches
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || 'Failed to update selection')
      }

      const data = await response.json()

      set({
        companyCount: data.company_count,
        countSemantic: data.count_semantic,
        nafCodes: data.naf_codes,
        activityMatches: data.activity_matches,
        isUpdatingSelection: false,
      })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred'
      set({ error: errorMessage, isUpdatingSelection: false })
      console.error('Error updating selection:', error)
    }
  },

  // Reset conversation (start fresh)
  resetConversation: () => {
    set({
      messages: [],
      extraction: null,
      companyCount: null,
      countSemantic: null,
      nafCodes: null,
      apiResult: null,
      activityMatches: null,
      error: null,
      isLoading: false,
      isUpdatingSelection: false,
    })
  },

  // Clear error message
  clearError: () => {
    set({ error: null })
  },
}))
