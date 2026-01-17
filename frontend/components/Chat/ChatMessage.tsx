'use client'

import { cn } from '@/lib/utils'
import { Bot, User } from 'lucide-react'

interface ChatMessageProps {
  message: {
    id: string
    role: 'user' | 'assistant'
    content: string
    created_at: string
  }
  compact?: boolean
}

export default function ChatMessage({ message, compact = false }: ChatMessageProps) {
  const isUser = message.role === 'user'

  if (compact) {
    return (
      <div className={cn('flex gap-2', isUser ? 'flex-row-reverse' : 'flex-row')}>
        {/* Small Avatar */}
        <div className={cn(
          'shrink-0 w-6 h-6 rounded-full flex items-center justify-center',
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-muted border border-border'
        )}>
          {isUser ? (
            <User className="h-3 w-3" />
          ) : (
            <Bot className="h-3 w-3 text-muted-foreground" />
          )}
        </div>

        {/* Compact Message bubble */}
        <div
          className={cn(
            'max-w-[80%] rounded-xl px-3 py-2',
            isUser
              ? 'bg-blue-600 text-white rounded-br-sm'
              : 'bg-muted/50 border border-border/50 rounded-bl-sm'
          )}
        >
          <div className={cn(
            'text-xs whitespace-pre-wrap break-words leading-relaxed',
            isUser ? 'text-white' : 'text-foreground'
          )}>
            {message.content}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div className={cn(
        'shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
        isUser
          ? 'bg-blue-600 text-white'
          : 'bg-muted border border-border'
      )}>
        {isUser ? (
          <User className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4 text-muted-foreground" />
        )}
      </div>

      {/* Message bubble */}
      <div
        className={cn(
          'max-w-[75%] rounded-2xl px-4 py-3',
          isUser
            ? 'bg-blue-600 text-white rounded-br-md'
            : 'bg-muted/50 border border-border/50 rounded-bl-md'
        )}
      >
        <div className={cn(
          'text-sm whitespace-pre-wrap break-words leading-relaxed',
          isUser ? 'text-white' : 'text-foreground'
        )}>
          {message.content}
        </div>
        <div className={cn(
          'text-[10px] mt-2',
          isUser ? 'text-white/60' : 'text-muted-foreground'
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
