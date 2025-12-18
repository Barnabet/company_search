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
    <div className="flex flex-col h-[600px] bg-white dark:bg-gray-900 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-500 to-primary-600 text-white px-6 py-4 rounded-t-lg">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold">💬 Recherche Conversationnelle</h2>
            <p className="text-sm text-primary-100 mt-1">
              Décrivez votre recherche, je vous aide à affiner les critères
            </p>
          </div>
          {hasMessages && (
            <button
              onClick={handleNewSearch}
              className="bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              Nouvelle recherche
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {!hasMessages && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🤖</div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              Comment puis-je vous aider ?
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Décrivez le type d'entreprises que vous recherchez
            </p>
            <div className="text-left max-w-md mx-auto space-y-2 text-sm text-gray-500 dark:text-gray-400">
              <p>💡 <strong>Exemples:</strong></p>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li>"Je cherche des PME dans la restauration"</li>
                <li>"Entreprises de construction en Bretagne"</li>
                <li>"Sociétés informatiques avec CA &gt; 1M€"</li>
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
            <div className="bg-gray-100 dark:bg-gray-800 rounded-lg px-4 py-3">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <div className="flex items-start">
              <span className="text-2xl mr-3">⚠️</span>
              <div className="flex-1">
                <h4 className="text-red-800 dark:text-red-300 font-semibold mb-1">
                  Erreur
                </h4>
                <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
              </div>
              <button
                onClick={clearError}
                className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Completion banner */}
        {isComplete && (
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
            <div className="flex items-center">
              <span className="text-2xl mr-3">✅</span>
              <div>
                <h4 className="text-green-800 dark:text-green-300 font-semibold">
                  Critères complétés !
                </h4>
                <p className="text-green-600 dark:text-green-400 text-sm">
                  Affichage des résultats ci-dessous
                </p>
              </div>
            </div>
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
              : 'Ex: Je cherche des PME dans la restauration'
          }
        />
      )}
    </div>
  )
}
