// columns.tsx
import { useState } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import type { StockPublic } from "@/client"
import { Sparkles, Download, Loader2 } from "lucide-react"
import { useMutation } from "@tanstack/react-query"

import { Button } from "@/components/ui/button"
import { StockActionsMenu } from "./StockActionsMenu"
import { StockNewsModal } from "./StockNewsModal"
import { StockAnalysisModal } from "./StockAnalysisModal"
import { AIDiveModal } from "./AIDiveModal"
import { OpenAPI } from "@/client" // Imports base URL configuration from generated client
/** API call to trigger downloading history for a stock symbol */
async function downloadStockHistory(symbol: string) {
  const baseUrl = OpenAPI.BASE || ""
 const endpoint = `${baseUrl}/api/v1/stocks/${encodeURIComponent(symbol)}/download-history`
  const res = await fetch(endpoint,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      },
    }
  )

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || "Failed to download stock history")
  }
    const t=res.json()
// @ts-ignore
    print(t)
  return res.json()
}

/** Helper function to convert raw Market Cap (INR) to Crores (Cr.) */
function formatMarketCapInCrores(value: number): string {
  if (!value || isNaN(value)) return "—"
  const inCrores = value / 10000000
  return `₹ ${inCrores.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr.`
}

/** Helper function to format Stock Price */
function formatPrice(value: number): string {
  if (value === undefined || value === null || isNaN(value)) return "—"
  return `₹ ${value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

/** Component handling actions for each row */
function ActionsCell({ stock }: { stock: StockPublic }) {
  const [isAiModalOpen, setIsAiModalOpen] = useState(false)
  const stockSymbol = stock.symbol || stock.name || ""

  // Declaration of downloadMutation using downloadStockHistory
  const downloadMutation = useMutation({
    mutationFn: (symbol: string) => downloadStockHistory(symbol),
    onSuccess: () => {
      alert(`Successfully downloaded history for ${stockSymbol}!`)
    },
    onError: (error: Error) => {
      alert(`Error downloading history: ${error.message}`)
    },
  })

  return (
    <div className="flex justify-end items-center gap-2">
      {/* 📥 Download History Button */}
      <Button
        variant="ghost"
        size="sm"
        disabled={downloadMutation.isPending}
        onClick={() => downloadMutation.mutate(stockSymbol)}
        title="Download Price History"
        className="h-8 w-8 p-0 text-zinc-400 hover:text-white hover:bg-zinc-800"
      >
        {downloadMutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
        ) : (
          <Download className="h-4 w-4" />
        )}
      </Button>

      {/* News Modal */}
      <StockNewsModal stockId={stock.id} stockSymbol={stockSymbol} />

      {/* ANZ / Pattern Analysis Modal */}
      <StockAnalysisModal stockId={stock.id} stockSymbol={stockSymbol} />

      {/* 🌟 AI Dive Trigger */}
      <button
        type="button"
        onClick={() => setIsAiModalOpen(true)}
        className="flex items-center gap-1 text-xs text-amber-500 font-medium hover:text-amber-400 hover:underline cursor-pointer"
      >
        <Sparkles className="h-3.5 w-3.5" />
        AI Dive
      </button>

      {/* Context Menu (3-dots) */}
      <StockActionsMenu stock={stock} />

      {/* AI Dive Modal */}
      <AIDiveModal
        isOpen={isAiModalOpen}
        onClose={() => setIsAiModalOpen(false)}
        stockSymbol={stockSymbol}
      />
    </div>
  )
}

export const columns: ColumnDef<StockPublic>[] = [
  {
    accessorKey: "symbol",
    header: "TICKER",
    cell: ({ row }) => (
      <span className="font-mono font-bold text-cyan-400 cursor-pointer hover:underline">
        {row.original.symbol}
      </span>
    ),
  },
  {
    accessorKey: "name",
    header: "STOCK DETAILS",
    cell: ({ row }) => {
      const name = row.original.name
      const description = row.original.description

      return (
        <div className="flex flex-col gap-0.5 py-1">
          <span className="font-bold text-base text-foreground block">
            {name === "nan" || !name ? row.original.symbol : name}
          </span>

          {description ? (
            <div
              className="text-xs text-muted-foreground italic max-w-xl truncate"
              dangerouslySetInnerHTML={{ __html: description }}
            />
          ) : (
            <span className="text-xs italic text-muted-foreground/60">
              No description
            </span>
          )}
        </div>
      )
    },
  },
  {
    accessorKey: "price",
    header: "PRICE",
    cell: ({ row }) => {
      const price = row.original.price
      return (
        <span className="font-semibold whitespace-nowrap text-foreground">
          {typeof price === "number" ? formatPrice(price) : "—"}
        </span>
      )
    },
  },
  {
    accessorKey: "market_cap",
    header: "MARKET CAP",
    cell: ({ row }) => {
      const cap = row.original.market_cap
      if (!cap) return <span className="text-muted-foreground/60 italic">—</span>

      return (
        <span className="whitespace-nowrap font-semibold text-foreground">
          {formatMarketCapInCrores(cap)}
        </span>
      )
    },
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => <ActionsCell stock={row.original} />,
  },
]