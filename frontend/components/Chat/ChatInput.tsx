/**
 * Chat input component for user messages
 */

import { useState, KeyboardEvent } from 'react'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = 'Votre message...',
}: ChatInputProps) {
  const [input, setInput] = useState('')

  const handleSend = () => {
    const trimmed = input.trim()
    if (trimmed && !disabled) {
      onSend(trimmed)
      setInput('')
    }
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
      <div className="flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg
                   resize-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500
                   dark:bg-gray-800 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed
                   placeholder-gray-400 dark:placeholder-gray-500"
          style={{ minHeight: '48px', maxHeight: '120px' }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white font-semibold
                   rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                   disabled:hover:bg-primary-600"
        >
          Envoyer
        </button>
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
        Appuyez sur Entrée pour envoyer, Shift+Entrée pour une nouvelle ligne
      </p>
    </div>
  )
}
