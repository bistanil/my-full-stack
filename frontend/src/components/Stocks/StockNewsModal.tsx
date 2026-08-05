// StockNewsModal.tsx
import { useQuery } from "@tanstack/react-query"
import { ExternalLink, ThumbsDown, ThumbsUp, Newspaper } from "lucide-react"
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

async function fetchNews(stockId: string) {
  const res = await fetch(`/api/v1/stocks/${stockId}/news`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("access_token")}`,
    },
  })
  if (!res.ok) throw new Error("Failed to fetch news")
  return res.json()
}

export function StockNewsModal({ stockId, stockSymbol }: { stockId: string; stockSymbol: string }) {
  const [open, setOpen] = useState(false)

  const { data: newsList, isLoading } = useQuery({
    queryKey: ["stock-news", stockId],
    queryFn: () => fetchNews(stockId),
    enabled: open,
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {/* Styled to match your dark table layout */}
        <Button
          variant="ghost"
          size="sm"
          className="h-8 gap-1.5 px-2 text-xs font-medium hover:bg-zinc-800 text-zinc-300 hover:text-white"
        >
          <Newspaper className="h-4 w-4" />
          <span>News</span>
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto bg-zinc-950 text-white border-zinc-800">
        <DialogHeader>
          <DialogTitle>Latest News & Sentiment: {stockSymbol}</DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="py-8 text-center text-sm text-zinc-400">
            Fetching news and running AI sentiment analysis...
          </div>
        ) : !newsList || newsList.length === 0 ? (
          <div className="py-8 text-center text-sm text-zinc-400">
            No recent news articles found for this stock.
          </div>
        ) : (
          <div className="flex flex-col gap-4 mt-2">
            {newsList.map((item: any) => {
              const isPositive = item.sentiment === "POSITIVE"
              const isNegative = item.sentiment === "NEGATIVE"

              return (
                <div key={item.id} className="border border-zinc-800 rounded-lg p-4 flex flex-col gap-3 bg-zinc-900/60">
                  <div className="flex items-start justify-between gap-3">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="font-medium text-sm hover:underline flex items-center gap-1.5 text-zinc-100"
                    >
                      {item.title}
                      <ExternalLink className="h-3.5 w-3.5 shrink-0 opacity-70" />
                    </a>
                    <Badge variant={isPositive ? "default" : isNegative ? "destructive" : "secondary"}>
                      {item.sentiment} ({item.score > 0 ? `+${item.score}` : item.score})
                    </Badge>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs pt-1">
                    {item.positive_points?.length > 0 && (
                      <div className="bg-emerald-500/10 text-emerald-400 p-2.5 rounded-md border border-emerald-500/20">
                        <span className="font-semibold flex items-center gap-1 mb-1">
                          <ThumbsUp className="h-3 w-3" /> Bullish Drivers
                        </span>
                        <ul className="list-disc list-inside space-y-1">
                          {item.positive_points.map((pt: string, idx: number) => (
                            <li key={idx}>{pt}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {item.negative_points?.length > 0 && (
                      <div className="bg-rose-500/10 text-rose-400 p-2.5 rounded-md border border-rose-500/20">
                        <span className="font-semibold flex items-center gap-1 mb-1">
                          <ThumbsDown className="h-3 w-3" /> Bearish Drivers
                        </span>
                        <ul className="list-disc list-inside space-y-1">
                          {item.negative_points.map((pt: string, idx: number) => (
                            <li key={idx}>{pt}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}