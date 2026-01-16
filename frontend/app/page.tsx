'use client'

import { useConversationStore } from '@/stores/conversationStore'
import SearchFieldsPanel from '@/components/SearchFieldsPanel'
import ChatPanel from '@/components/Chat/ChatPanel'
import { ModeToggle } from '@/components/mode-toggle'

export default function Home() {
  const {
    extraction,
    companyCount,
    activityMatches,
    isLoading,
    isUpdatingSelection,
    updateActivitySelection
  } = useConversationStore()

  return (
    <main className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b px-6 py-4 shrink-0 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Company Search</h1>
          <p className="text-sm text-muted-foreground">
            Recherche d&apos;entreprises par critères
          </p>
        </div>
        <ModeToggle />
      </header>

      {/* Two-panel layout: Chat left, Results right */}
      <div className="flex flex-col lg:flex-row flex-1 overflow-hidden">
        {/* Left Panel - Chat */}
        <div className="flex-1 flex flex-col p-4 overflow-hidden border-b lg:border-b-0 lg:border-r">
          <ChatPanel />
        </div>

        {/* Right Panel - Search Fields & Results */}
        <aside className="w-full lg:w-80 xl:w-96 bg-muted/30 overflow-y-auto shrink-0">
          <SearchFieldsPanel
            extraction={extraction}
            companyCount={companyCount}
            activityMatches={activityMatches}
            isLoading={isLoading}
            isUpdatingSelection={isUpdatingSelection}
            onActivitySelect={updateActivitySelection}
          />
        </aside>
      </div>
    </main>
  )
}
