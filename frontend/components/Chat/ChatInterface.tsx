/**
 * Main chat interface component for conversational agent
 */

'use client'

import { useEffect, useRef } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'
import type { ExtractionResult } from '@/types/conversation'

interface ChatInterfaceProps {
  onExtractionComplete: (result: ExtractionResult) => void
}

export default function ChatInterface({ onExtractionComplete }: ChatInterfaceProps) {
  const {
    currentConversation,
    isLoading,
    error,
    startConversation,
    sendMessage,
    resetConversation,
    clearError,
  } = useConversationStore()

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentConversation?.messages])

  // Handle extraction completion
  useEffect(() => {
    if (
      currentConversation?.status === 'completed' &&
      currentConversation.extraction_result
    ) {
      onExtractionComplete(currentConversation.extraction_result)
    }
  }, [currentConversation, onExtractionComplete])

  const handleSendMessage = (message: string) => {
    if (currentConversation) {
      sendMessage(message)
    } else {
      startConversation(message)
    }
  }

  const handleNewSearch = () => {
    resetConversation()
    clearError()
  }

  const isComplete = currentConversation?.status === 'completed'
  const hasMessages = currentConversation && currentConversation.messages.length > 0

  return (
    <div className="flex flex-col h-[500px] bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="bg-gray-50 dark:bg-gray-900 px-4 py-3 rounded-t-lg border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Assistant de recherche</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Décrivez votre recherche d'entreprises
            </p>
          </div>
          {hasMessages && (
            <button
              onClick={handleNewSearch}
              className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              Nouvelle recherche
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {!hasMessages && (
          <div className="text-center py-8">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
              Comment puis-je vous aider ?
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
              Décrivez le type d'entreprises recherchées
            </p>
            <div className="text-left max-w-sm mx-auto space-y-1 text-xs text-gray-500 dark:text-gray-400">
              <p className="font-medium">Exemples :</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>PME dans la restauration</li>
                <li>Entreprises de construction en Bretagne</li>
                <li>Sociétés informatiques avec CA &gt; 1M€</li>
              </ul>
            </div>
          </div>
        )}

        {hasMessages &&
          currentConversation.messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-3 py-2">
              <div className="flex items-center space-x-1">
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </div>
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
            <div className="flex items-start justify-between">
              <p className="text-red-600 dark:text-red-400 text-xs">{error}</p>
              <button
                onClick={clearError}
                className="text-red-400 hover:text-red-600 text-xs ml-2"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Completion banner */}
        {isComplete && (
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
            <p className="text-green-700 dark:text-green-400 text-xs font-medium">
              Critères extraits avec succès
            </p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      {!isComplete && (
        <ChatInput
          onSend={handleSendMessage}
          disabled={isLoading}
          placeholder={
            hasMessages
              ? 'Votre réponse...'
              : 'Ex: PME informatique en Bretagne'
          }
        />
      )}
    </div>
  )
}
