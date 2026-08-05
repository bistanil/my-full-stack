// StockAnalysisModal.tsx
import { useQuery } from "@tanstack/react-query"
import { LineChart, TrendingUp, TrendingDown, Minus } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { OpenAPI } from "@/client"

// Updated Pattern item interface to match FastAPI Pydantic schema
export interface PatternItem {
  id: string
  stock_id?: string
  stock_symbol?: string
  pattern_date: string
  pattern_category?: string
  pattern_name: string
  signal: "BUY" | "SELL" | "NEUTRAL" | string
  strength?: number
  confidence?: number
  score?: number
}

async function fetchPatterns(stockId: string): Promise<PatternItem[]> {
  const token = localStorage.getItem("access_token")
  const baseUrl = OpenAPI.BASE || ""
  const endpoint = `${baseUrl}/api/v1/stocks/${encodeURIComponent(stockId)}/patterns`

  const res = await fetch(endpoint, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || "Failed to fetch technical patterns")
  }

  const json = await res.json()

  // Safely extract array from { data: [...], count: X } or raw array
  if (Array.isArray(json)) return json
  if (Array.isArray(json.data)) return json.data
  if (Array.isArray(json.patterns)) return json.patterns
  if (Array.isArray(json.items)) return json.items

  return []
}

export function StockAnalysisModal({stockId, stockSymbol,}: { stockId: string; stockSymbol: string }) {
  const [open, setOpen] = useState(false)

  const { data: patternList = [], isLoading, isError } = useQuery({
    queryKey: ["stock-patterns", stockId],
    queryFn: () => fetchPatterns(stockId),
    enabled: open && Boolean(stockId),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 gap-1.5 px-2 text-xs font-medium hover:bg-zinc-800 text-cyan-400 hover:text-cyan-300"
        >
          <LineChart className="h-4 w-4" />
          <span>ANZ</span>
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto bg-zinc-950 text-white border-zinc-800">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <LineChart className="h-5 w-5 text-cyan-400" />
            <span>Technical Pattern Analysis: {stockSymbol}</span>
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="py-8 text-center text-sm text-zinc-400">
            Scanning stock chart patterns and running signal analysis...
          </div>
        ) : isError ? (
          <div className="py-8 text-center text-sm text-rose-400">
            Error fetching pattern data. Please verify authorization and backend logs.
          </div>
        ) : patternList.length === 0 ? (
          <div className="py-8 text-center text-sm text-zinc-400">
            No technical pattern signals detected for this stock.
          </div>
        ) : (
          <div className="mt-2 border border-zinc-800 rounded-lg overflow-hidden bg-zinc-900/60">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-900 border-b border-zinc-800 text-zinc-400 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="p-3">Symbol</th>
                  <th className="p-3">Date</th>
                  <th className="p-3">Pattern</th>
                  <th className="p-3">Signal</th>
                  <th className="p-3 text-right">Strength</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {patternList.map((item) => {
                  const signalUpper = (item.signal || "NEUTRAL").toUpperCase()
                  const isBuy = signalUpper === "BUY"
                  const isSell = signalUpper === "SELL"

                  // Fallback score values depending on API output keys
                  const rawStrength =
                    item.strength ?? item.confidence ?? item.score ?? 0

                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-zinc-800/40 transition-colors"
                    >
                      <td className="p-3 font-mono font-bold text-cyan-400">
                        {item.stock_symbol || stockSymbol}
                      </td>
                      <td className="p-3 font-mono text-zinc-400">
                        {item.pattern_date}
                      </td>
                      <td className="p-3">
                        <div className="flex flex-col gap-0.5">
                          <span className="font-semibold text-zinc-100">
                            {item.pattern_name}
                          </span>
                          {item.pattern_category && (
                            <span className="text-[10px] text-zinc-500">
                              {item.pattern_category}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="p-3">
                        <Badge
                          variant={
                            isBuy
                              ? "default"
                              : isSell
                              ? "destructive"
                              : "secondary"
                          }
                          className={`gap-1 text-[11px] font-semibold ${
                            isBuy
                              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
                              : isSell
                              ? "bg-rose-500/15 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20"
                              : "bg-zinc-800 text-zinc-300"
                          }`}
                        >
                          {isBuy ? (
                            <TrendingUp className="h-3 w-3" />
                          ) : isSell ? (
                            <TrendingDown className="h-3 w-3" />
                          ) : (
                            <Minus className="h-3 w-3" />
                          )}
                          {signalUpper}
                        </Badge>
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 bg-zinc-800 h-1.5 rounded-full overflow-hidden hidden sm:block">
                            <div
                              className={`h-full rounded-full ${
                                isBuy
                                  ? "bg-emerald-500"
                                  : isSell
                                  ? "bg-rose-500"
                                  : "bg-zinc-400"
                              }`}
                              style={{
                                width: `${Math.min(
                                  Math.max(rawStrength, 0),
                                  100
                                )}%`,
                              }}
                            />
                          </div>
                          <span className="font-mono font-medium text-zinc-200">
                            {rawStrength}
                          </span>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}