'use client'

import { useConversationStore } from '@/stores/conversationStore'
import SearchFieldsPanel from '@/components/SearchFieldsPanel'
import ChatSection from '@/components/Chat/ChatSection'
import { ModeToggle } from '@/components/mode-toggle'
import { cn } from '@/lib/utils'

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

  // Transition happens as soon as user sends first message
  const hasStarted = messages.length > 0
  // Criteria section only shows when we have results
  const hasResults = extraction !== null

  return (
    <main className="h-screen bg-background flex flex-col overflow-hidden">
      {/* Theme toggle - floating top right */}
      <div className="absolute top-4 right-4 z-10">
        <ModeToggle />
      </div>

      {/* Chat Section - Animated height transition */}
      <div
        className={cn(
          "shrink-0 transition-all duration-500 ease-out",
          hasStarted ? "h-[40vh]" : "h-screen"
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
    </main>
  )
}
