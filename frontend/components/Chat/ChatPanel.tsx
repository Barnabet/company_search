'use client'

import { useEffect, useRef, useState, KeyboardEvent } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import ChatMessage from './ChatMessage'
import { Send, RotateCcw, Loader2, Sparkles, Search, ArrowRight } from 'lucide-react'

const EXAMPLE_QUERIES = [
  { text: "PME dans la restauration en Ile-de-France", icon: "restaurant" },
  { text: "Startups tech créées après 2020", icon: "tech" },
  { text: "Entreprises BTP avec +50 salariés", icon: "construction" },
]

interface ChatPanelProps {
  compact?: boolean
}

export default function ChatPanel({ compact = false }: ChatPanelProps) {
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

  // Compact mode for stacked layout
  if (compact) {
    return (
      <div className="h-full flex flex-col overflow-hidden">
        {/* Messages Area - Compact */}
        <div className="flex-1 overflow-hidden">
          <ScrollArea className="h-full" ref={scrollRef}>
            <div className="px-6 py-3">
              {!hasMessages ? (
                // Compact empty state
                <div className="flex items-center justify-center gap-8 py-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20">
                      <Sparkles className="h-5 w-5 text-blue-500" />
                    </div>
                    <div>
                      <h2 className="text-sm font-semibold">Décrivez votre recherche</h2>
                      <p className="text-xs text-muted-foreground">Langage naturel accepté</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {EXAMPLE_QUERIES.map((example, idx) => (
                      <button
                        key={idx}
                        className="text-xs px-3 py-1.5 rounded-lg border border-border/50 bg-muted/30 hover:bg-muted/50 hover:border-blue-500/30 transition-all duration-200 max-w-[200px] truncate"
                        onClick={() => setInput(example.text)}
                      >
                        {example.text}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Conversation</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleNewSearch}
                      className="text-xs text-muted-foreground hover:text-foreground h-6 px-2"
                    >
                      <RotateCcw className="h-3 w-3 mr-1" />
                      Nouvelle
                    </Button>
                  </div>
                  {messages.map((message) => (
                    <ChatMessage key={message.id} message={message} compact />
                  ))}
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="bg-muted/50 rounded-lg px-3 py-2 flex items-center gap-2 text-xs">
                        <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
                        <span className="text-muted-foreground">Analyse...</span>
                      </div>
                    </div>
                  )}
                  {error && (
                    <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-2 text-xs text-destructive">
                      {error}
                    </div>
                  )}
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Compact Input Area */}
        <div className="border-t bg-background/80 backdrop-blur-sm px-6 py-3">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={hasMessages ? 'Affinez votre recherche...' : 'Ex: PME informatique en Bretagne'}
                disabled={isLoading}
                className="pl-10 pr-4 h-10 rounded-xl border-border/50 bg-muted/30 focus:bg-background transition-colors"
              />
            </div>
            <Button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              size="icon"
              className="h-10 w-10 rounded-xl bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20 transition-all duration-200 disabled:opacity-50 disabled:shadow-none"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Full mode (original)
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Messages Area */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full" ref={scrollRef}>
          <div className="p-6 max-w-3xl mx-auto">
            {!hasMessages ? (
              // Empty state with better visual design
              <div className="flex flex-col items-center justify-center py-16 px-4">
                <div className="relative mb-6">
                  <div className="absolute inset-0 bg-blue-500/20 blur-2xl rounded-full" />
                  <div className="relative p-4 rounded-2xl bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20">
                    <Sparkles className="h-8 w-8 text-blue-500" />
                  </div>
                </div>

                <h2 className="text-xl font-semibold mb-2 text-center">
                  Décrivez votre recherche
                </h2>
                <p className="text-sm text-muted-foreground mb-8 text-center max-w-md">
                  Utilisez le langage naturel pour trouver des entreprises françaises selon vos critères
                </p>

                <div className="w-full max-w-lg space-y-2">
                  <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wider">
                    Exemples de recherches
                  </p>
                  {EXAMPLE_QUERIES.map((example, idx) => (
                    <button
                      key={idx}
                      className="group w-full text-left p-3 rounded-xl border border-border/50 bg-muted/30 hover:bg-muted/50 hover:border-blue-500/30 transition-all duration-200"
                      onClick={() => setInput(example.text)}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm">{example.text}</span>
                        <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200" />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {/* New search button */}
                <div className="flex justify-end mb-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleNewSearch}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    <RotateCcw className="h-3 w-3 mr-1.5" />
                    Nouvelle recherche
                  </Button>
                </div>

                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}

                {/* Loading indicator */}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-muted/50 backdrop-blur-sm rounded-2xl px-4 py-3 flex items-center gap-3 border border-border/50">
                      <div className="relative">
                        <div className="absolute inset-0 bg-blue-500/30 blur-md rounded-full" />
                        <Loader2 className="relative h-4 w-4 animate-spin text-blue-500" />
                      </div>
                      <span className="text-sm text-muted-foreground">Analyse en cours...</span>
                    </div>
                  </div>
                )}

                {/* Error message */}
                {error && (
                  <div className="bg-destructive/10 border border-destructive/20 rounded-xl p-4">
                    <p className="text-destructive text-sm">{error}</p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={clearError}
                      className="text-xs mt-2 h-7 px-2"
                    >
                      Fermer
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Input Area - Modern floating design */}
      <div className="border-t bg-background/80 backdrop-blur-sm p-4">
        <div className="max-w-3xl mx-auto">
          <div className="relative flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={hasMessages ? 'Affinez votre recherche...' : 'Décrivez les entreprises que vous recherchez...'}
                disabled={isLoading}
                className="pl-10 pr-4 h-11 rounded-xl border-border/50 bg-muted/30 focus:bg-background transition-colors"
              />
            </div>
            <Button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              size="icon"
              className="h-11 w-11 rounded-xl bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/20 transition-all duration-200 disabled:opacity-50 disabled:shadow-none"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-[11px] text-muted-foreground mt-2 text-center">
            Appuyez sur <kbd className="px-1.5 py-0.5 rounded bg-muted text-[10px] font-mono">Entrée</kbd> pour envoyer
          </p>
        </div>
      </div>
    </div>
  )
}
