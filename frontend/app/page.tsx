'use client'

import { useConversationStore } from '@/stores/conversationStore'
import SearchFieldsPanel from '@/components/SearchFieldsPanel'
import ChatPanel from '@/components/Chat/ChatPanel'

export default function Home() {
  const {
    getCurrentExtraction,
    getCompanyCount,
    isLoading
  } = useConversationStore()

  const extraction = getCurrentExtraction()
  const companyCount = getCompanyCount()

  return (
    <main className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b px-6 py-4 shrink-0">
        <h1 className="text-xl font-semibold">Company Search</h1>
        <p className="text-sm text-muted-foreground">
          Recherche d&apos;entreprises par critères
        </p>
      </header>

      {/* Two-panel layout */}
      <div className="flex flex-col lg:flex-row flex-1 overflow-hidden">
        {/* Left Panel - Search Fields */}
        <aside className="w-full lg:w-80 xl:w-96 border-b lg:border-b-0 lg:border-r bg-muted/30 overflow-y-auto shrink-0">
          <SearchFieldsPanel
            extraction={extraction}
            companyCount={companyCount}
            isLoading={isLoading}
          />
        </aside>

        {/* Right Panel - Chat */}
        <div className="flex-1 flex flex-col p-4 overflow-hidden">
          <ChatPanel />
        </div>
      </div>
    </main>
  )
}
