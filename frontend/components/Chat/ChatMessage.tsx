/**
 * Individual chat message component
 */

import type { Message } from '@/types/conversation'

interface ChatMessageProps {
  message: Message
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 animate-slideIn`}
    >
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
        }`}
      >
        {/* Role label (only for assistant) */}
        {isAssistant && (
          <div className="text-xs font-semibold text-primary-600 dark:text-primary-400 mb-1">
            Agent
          </div>
        )}

        {/* Message content */}
        <div className="text-sm whitespace-pre-wrap break-words">
          {message.content}
        </div>

        {/* Timestamp */}
        <div
          className={`text-xs mt-2 ${
            isUser ? 'text-primary-100' : 'text-gray-500 dark:text-gray-400'
          }`}
        >
          {new Date(message.created_at).toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
    </div>
  )
}
