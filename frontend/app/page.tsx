'use client'

import { useState } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import SearchFieldsPanel from '@/components/SearchFieldsPanel'
import ChatSection from '@/components/Chat/ChatSection'
import { ModeToggle } from '@/components/mode-toggle'
import { cn } from '@/lib/utils'
import { ChevronRight, X, Building2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function Home() {
  const {
    messages,
    extraction,
    companyCount,
    activityMatches,
    isLoading,
    isUpdatingSelection,
    updateActivitySelection,
    sendMessage,
    resetConversation,
    error,
    clearError,
  } = useConversationStore()

  const [showResultsPanel, setShowResultsPanel] = useState(false)

  // Transition happens as soon as user sends first message
  const hasStarted = messages.length > 0
  // Criteria section only shows when we have results
  const hasResults = extraction !== null
  // Color based on count
  const isGoodCount = companyCount !== null && companyCount <= 500

  return (
    <main className="h-screen bg-background flex flex-col overflow-hidden">
      {/* Theme toggle - floating top right */}
      <div className="absolute top-4 right-4 z-20">
        <ModeToggle />
      </div>

      {/* Chat Section - Animated height transition */}
      <div
        className={cn(
          "shrink-0 transition-all duration-500 ease-out relative",
          hasStarted ? "h-1/2" : "h-screen"
        )}
      >
        <ChatSection
          messages={messages}
          isLoading={isLoading}
          error={error}
          onSendMessage={sendMessage}
          onReset={resetConversation}
          onClearError={clearError}
          expanded={!hasStarted}
        />

        {/* Floating Results Button - bottom right of chat section */}
        {hasResults && companyCount !== null && (
          <button
            onClick={() => setShowResultsPanel(true)}
            className={cn(
              "absolute bottom-4 right-4 flex items-center gap-2 px-4 py-2.5 rounded-full shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl",
              isGoodCount
                ? "bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-blue-500/25"
                : "bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-amber-500/25"
            )}
          >
            <span className="font-bold text-lg">{companyCount.toLocaleString('fr-FR')}</span>
            <span className="text-sm opacity-90">résultats</span>
            <ChevronRight className="h-5 w-5 ml-1" />
          </button>
        )}
      </div>

      {/* Criteria Section - Pops up from bottom when results arrive */}
      <div
        className={cn(
          "flex-1 border-t overflow-hidden transition-all duration-500 ease-out",
          hasStarted ? "block" : "hidden",
          hasResults
            ? "opacity-100 translate-y-0"
            : "opacity-0 translate-y-full"
        )}
      >
        <div className="h-full overflow-y-auto">
          <SearchFieldsPanel
            extraction={extraction}
            companyCount={companyCount}
            activityMatches={activityMatches}
            isLoading={isLoading}
            isUpdatingSelection={isUpdatingSelection}
            onActivitySelect={updateActivitySelection}
            fullWidth
          />
        </div>
      </div>

      {/* Slide-in Results Panel */}
      <div
        className={cn(
          "fixed inset-y-0 right-0 w-full max-w-lg bg-background border-l shadow-2xl z-50 transition-transform duration-300 ease-out",
          showResultsPanel ? "translate-x-0" : "translate-x-full"
        )}
      >
        {/* Panel Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-3">
            <div className={cn(
              "p-2 rounded-lg",
              isGoodCount ? "bg-blue-500/10" : "bg-amber-500/10"
            )}>
              <Building2 className={cn(
                "h-5 w-5",
                isGoodCount ? "text-blue-500" : "text-amber-500"
              )} />
            </div>
            <div>
              <h2 className="font-semibold">Résultats de recherche</h2>
              <p className="text-sm text-muted-foreground">
                {companyCount !== null ? `${companyCount.toLocaleString('fr-FR')} entreprises trouvées` : 'Chargement...'}
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowResultsPanel(false)}
            className="rounded-full"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Panel Content - Placeholder */}
        <div className="p-6 h-full overflow-y-auto">
          <div className="space-y-4">
            {/* Status Message */}
            <div className={cn(
              "rounded-xl p-4 border",
              isGoodCount
                ? "bg-blue-500/5 border-blue-500/20"
                : "bg-amber-500/5 border-amber-500/20"
            )}>
              {isGoodCount ? (
                <p className="text-sm">
                  <span className="font-medium text-blue-600 dark:text-blue-400">Prêt pour export!</span>
                  <br />
                  <span className="text-muted-foreground">Vous pouvez exporter jusqu&apos;à 500 entreprises.</span>
                </p>
              ) : (
                <p className="text-sm">
                  <span className="font-medium text-amber-600 dark:text-amber-400">Trop de résultats</span>
                  <br />
                  <span className="text-muted-foreground">Affinez vos critères pour réduire à 500 maximum.</span>
                </p>
              )}
            </div>

            {/* Placeholder Company List */}
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                Aperçu des entreprises
              </h3>
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="rounded-xl border border-border/50 bg-muted/20 p-4 animate-pulse"
                >
                  <div className="h-4 bg-muted rounded w-3/4 mb-2" />
                  <div className="h-3 bg-muted/60 rounded w-1/2 mb-3" />
                  <div className="flex gap-2">
                    <div className="h-5 bg-muted/40 rounded-full w-16" />
                    <div className="h-5 bg-muted/40 rounded-full w-20" />
                  </div>
                </div>
              ))}
            </div>

            {/* Coming Soon Notice */}
            <div className="text-center py-8">
              <p className="text-sm text-muted-foreground">
                Liste détaillée des entreprises bientôt disponible
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Backdrop for results panel */}
      {showResultsPanel && (
        <div
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 transition-opacity"
          onClick={() => setShowResultsPanel(false)}
        />
      )}
    </main>
  )
}
