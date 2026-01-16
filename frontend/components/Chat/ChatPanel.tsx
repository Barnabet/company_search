'use client'

import { useEffect, useRef, useState, KeyboardEvent } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import ChatMessage from './ChatMessage'
import { Send, RotateCcw, Loader2 } from 'lucide-react'

const EXAMPLE_QUERIES = [
  "PME dans la restauration en Ile-de-France",
  "Entreprises informatiques créées après 2020",
  "Sociétés de construction avec plus de 50 salariés",
]

export default function ChatPanel() {
  const {
    messages,
    isLoading,
    error,
    sendMessage,
    resetConversation,
    clearError,
  } = useConversationStore()

  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }, [messages])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return

    sendMessage(trimmed)
    setInput('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleNewSearch = () => {
    resetConversation()
    clearError()
    setInput('')
  }

  const hasMessages = messages.length > 0

  return (
    <Card className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-2 border-b">
        <div>
          <CardTitle className="text-base">Assistant de recherche</CardTitle>
          <p className="text-xs text-muted-foreground">
            Décrivez le type d&apos;entreprises recherchées
          </p>
        </div>
        {hasMessages && (
          <Button variant="ghost" size="sm" onClick={handleNewSearch}>
            <RotateCcw className="h-4 w-4 mr-2" />
            Nouvelle recherche
          </Button>
        )}
      </CardHeader>

      {/* Messages Area */}
      <CardContent className="flex-1 overflow-hidden p-0">
        <ScrollArea className="h-full" ref={scrollRef}>
          <div className="p-4">
            {!hasMessages ? (
              // Empty state with examples
              <div className="flex flex-col items-center justify-center py-12">
                <h3 className="text-sm font-medium mb-2">
                  Comment puis-je vous aider ?
                </h3>
                <p className="text-xs text-muted-foreground mb-4">
                  Exemples de recherches :
                </p>
                <div className="space-y-2 w-full max-w-md">
                  {EXAMPLE_QUERIES.map((example, idx) => (
                    <Button
                      key={idx}
                      variant="outline"
                      size="sm"
                      className="text-xs w-full justify-start h-auto py-2 px-3"
                      onClick={() => setInput(example)}
                    >
                      {example}
                    </Button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}

                {/* Loading indicator */}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-lg px-3 py-2 flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span className="text-sm">Analyse en cours...</span>
                    </div>
                  </div>
                )}

                {/* Error message */}
                {error && (
                  <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3">
                    <p className="text-destructive text-xs">{error}</p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={clearError}
                      className="text-xs mt-1 h-6 px-2"
                    >
                      Fermer
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>

      {/* Input Area - ALWAYS visible */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={hasMessages ? 'Affinez votre recherche...' : 'Ex: PME informatique en Bretagne'}
            disabled={isLoading}
            className="flex-1"
          />
          <Button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            size="icon"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Appuyez sur Entrée pour envoyer
        </p>
      </div>
    </Card>
  )
}
