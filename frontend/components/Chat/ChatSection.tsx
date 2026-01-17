'use client'

import { useState, KeyboardEvent, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Send, RotateCcw, Loader2, Search } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

interface ChatSectionProps {
  messages: Message[]
  isLoading: boolean
  error: string | null
  onSendMessage: (content: string) => void
  onReset: () => void
  onClearError: () => void
  expanded: boolean
}

const EXAMPLE_QUERIES = [
  "PME dans la restauration en Ile-de-France",
  "Startups tech avec plus de 10 salariés",
  "Entreprises BTP en Bretagne",
]

export default function ChatSection({
  messages,
  isLoading,
  error,
  onSendMessage,
  onReset,
  onClearError,
  expanded,
}: ChatSectionProps) {
  const [input, setInput] = useState('')
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [displayMessages, setDisplayMessages] = useState<Message[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const prevMessagesRef = useRef<Message[]>([])
  const newMessageIds = useRef<Set<string>>(new Set())

  // Handle message changes and animations
  useEffect(() => {
    if (messages.length === 0) {
      setDisplayMessages([])
      newMessageIds.current.clear()
      prevMessagesRef.current = []
      return
    }

    const lastMsg = messages[messages.length - 1]
    const prevMessages = prevMessagesRef.current
    const hadCompleteRound = prevMessages.length >= 2 &&
      prevMessages[prevMessages.length - 1]?.role === 'assistant'

    // New user message after a complete round - trigger transition
    if (lastMsg.role === 'user' && hadCompleteRound) {
      setIsTransitioning(true)
      newMessageIds.current.clear()
      newMessageIds.current.add(lastMsg.id)

      // After slide-out animation, show new message
      setTimeout(() => {
        setDisplayMessages([lastMsg])
        setIsTransitioning(false)
      }, 300)
    }
    // New assistant message - add it with animation
    else if (lastMsg.role === 'assistant') {
      setDisplayMessages(prev => {
        if (prev.find(m => m.id === lastMsg.id)) return prev
        newMessageIds.current.add(lastMsg.id)
        // Get the user message before this assistant message
        const userMsg = messages[messages.length - 2]
        return userMsg ? [userMsg, lastMsg] : [lastMsg]
      })
    }
    // First user message or continuing without complete round
    else {
      setDisplayMessages(prev => {
        if (prev.find(m => m.id === lastMsg.id)) return prev
        newMessageIds.current.add(lastMsg.id)
        return [lastMsg]
      })
    }

    prevMessagesRef.current = [...messages]
  }, [messages])

  // Clear animation flags after they've played
  useEffect(() => {
    if (displayMessages.length > 0) {
      const timer = setTimeout(() => {
        newMessageIds.current.clear()
      }, 350)
      return () => clearTimeout(timer)
    }
  }, [displayMessages])


  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return
    onSendMessage(trimmed)
    setInput('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="h-full relative overflow-hidden">
      {/* Header content - only visible when expanded */}
      <div
        className={cn(
          "absolute inset-x-0 top-1/2 -translate-y-1/2 flex flex-col items-center px-6 transition-all duration-500 ease-out",
          expanded
            ? "opacity-100"
            : "opacity-0 -translate-y-[150%] pointer-events-none"
        )}
        style={{ paddingBottom: '80px' }} // Space for the input bar
      >
        {/* Title */}
        <div className="text-center mb-4">
          <h1 className="text-2xl font-bold mb-2">Company Search</h1>
          <p className="text-muted-foreground">
            Recherchez des entreprises françaises en langage naturel
          </p>
        </div>
      </div>

      {/* THE SEARCH BAR - Single element that animates position */}
      <div
        className={cn(
          "absolute left-0 right-0 transition-all duration-500 ease-out z-10",
          expanded
            ? "top-1/2 translate-y-[10px] px-6"
            : "top-4 translate-y-0 pl-6 pr-20"
        )}
      >
        {/* Inner wrapper for width animation */}
        <div
          className="mx-auto transition-all duration-500 ease-out"
          style={{
            maxWidth: expanded ? '672px' : '100%', // 672px = max-w-2xl
          }}
        >
        <div className="flex items-center gap-3">
          <div className={cn(
            "relative flex-1 transition-all duration-500",
          )}>
            <Search className={cn(
              "absolute top-1/2 -translate-y-1/2 text-muted-foreground transition-all duration-300",
              expanded ? "left-4 h-5 w-5" : "left-3 h-4 w-4"
            )} />
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={expanded ? "Décrivez les entreprises que vous recherchez..." : "Affinez votre recherche..."}
              disabled={isLoading}
              className={cn(
                "border-border/50 bg-background transition-all duration-500",
                expanded
                  ? "pl-12 pr-14 h-14 text-base rounded-2xl"
                  : "pl-10 pr-4 h-11 rounded-xl"
              )}
            />
            {/* Send button inside input - only when expanded */}
            {expanded && (
              <Button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                size="icon"
                className="absolute right-2 top-1/2 -translate-y-1/2 h-10 w-10 rounded-xl bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20 transition-all duration-200 disabled:opacity-50 disabled:shadow-none"
              >
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            )}
          </div>

          {/* Buttons - only when compact */}
          {!expanded && (
            <>
              <Button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                size="icon"
                className="h-11 w-11 rounded-xl bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20 transition-all duration-200 disabled:opacity-50 disabled:shadow-none"
              >
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={onReset}
                className="h-11 w-11 rounded-xl text-muted-foreground hover:text-foreground"
                title="Nouvelle recherche"
              >
                <RotateCcw className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
        </div>
      </div>

      {/* Example queries - only visible when expanded */}
      <div
        className={cn(
          "absolute left-1/2 -translate-x-1/2 top-1/2 translate-y-[90px] transition-all duration-500 ease-out",
          expanded
            ? "opacity-100"
            : "opacity-0 pointer-events-none"
        )}
      >
        <div className="flex flex-wrap gap-2 justify-center">
          {EXAMPLE_QUERIES.map((example, idx) => (
            <button
              key={idx}
              onClick={() => setInput(example)}
              className="text-sm px-4 py-2 rounded-full border border-border/50 bg-muted/30 hover:bg-muted/50 hover:border-blue-500/30 transition-all duration-200"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {/* Messages - only visible when compact */}
      <div
        className={cn(
          "absolute inset-x-0 top-[76px] bottom-0 px-6 pb-4 overflow-hidden transition-all duration-500 ease-out",
          expanded
            ? "opacity-0 translate-y-4 pointer-events-none"
            : "opacity-100 translate-y-0"
        )}
      >
        <div className="h-full overflow-hidden">
          <div className={cn(
            "space-y-3 transition-all duration-300",
            isTransitioning && "animate-slideUp"
          )}>
            {displayMessages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  'flex gap-2',
                  message.role === 'user' ? 'justify-end' : 'justify-start',
                  newMessageIds.current.has(message.id) && (
                    message.role === 'user' ? 'animate-slideInFromRight' : 'animate-slideInFromLeft'
                  )
                )}
              >
                <div
                  className={cn(
                    'max-w-[85%] rounded-xl px-4 py-2.5',
                    message.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-sm'
                      : 'bg-muted/50 border border-border/50 rounded-bl-sm'
                  )}
                >
                  <p className="text-sm leading-relaxed">{message.content}</p>
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <div className="flex justify-start animate-slideInFromLeft">
                <div className="bg-muted/50 rounded-xl px-4 py-2.5 flex items-center gap-2 border border-border/50">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                  <span className="text-sm text-muted-foreground">Analyse...</span>
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="bg-destructive/10 border border-destructive/20 rounded-xl p-3 text-sm text-destructive animate-slideInFromLeft">
                {error}
                <button onClick={onClearError} className="ml-2 underline">Fermer</button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
