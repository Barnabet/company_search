'use client'

import { cn } from '@/lib/utils'

interface ChatMessageProps {
  message: {
    id: string
    role: 'user' | 'assistant'
    content: string
    created_at: string
  }
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-3',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-foreground'
        )}
      >
        {!isUser && (
          <div className="text-xs font-semibold text-primary mb-1">
            Agent
          </div>
        )}
        <div className="text-sm whitespace-pre-wrap break-words">
          {message.content}
        </div>
        <div className={cn(
          'text-xs mt-2',
          isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
        )}>
          {new Date(message.created_at).toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
    </div>
  )
}
