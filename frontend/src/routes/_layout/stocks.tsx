import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Search, ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react"
import { useState, useRef, useEffect } from "react"

import { StocksService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import UploadStocksModal from "@/components/Stocks/UploadStocksModal"
import { columns } from "@/components/Stocks/columns"
import PendingItems from "@/components/Pending/PendingItems"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
const PER_PAGE = 10

export const Route = createFileRoute("/_layout/stocks")({
  component: Stocks,
  head: () => ({
    meta: [
      {
        title: "Stocks - FastAPI Template",
      },
    ],
  }),
})

function getPaginationRange(currentPage: number, totalPages: number) {
  const delta = 1
  const range: (number | string)[] = []

  for (let i = 1; i <= totalPages; i++) {
    if (
      i === 1 ||
      i === totalPages ||
      (i >= currentPage - delta && i <= currentPage + delta)
    ) {
      range.push(i)
    } else if (range[range.length - 1] !== "...") {
      range.push("...")
    }
  }

  return range
}

function StocksTableContent() {
  const [page, setPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  const skip = (page - 1) * PER_PAGE

  const { data: stocksResponse, isLoading } = useQuery({
    queryKey: ["stocks", page, searchQuery],
    queryFn: () =>
      StocksService.readStocks({
        skip,
        limit: PER_PAGE,
        search: searchQuery || undefined,
      } as any),
  })

  const stocks = Array.isArray(stocksResponse)
    ? stocksResponse
    : stocksResponse?.data ?? []

  const totalCount = stocksResponse?.count ?? stocks.length
  const totalPages = Math.ceil(totalCount / PER_PAGE) || 1

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value)
    setPage(1)
  }

  // Restore input focus if component re-renders
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }, [stocksResponse])

  const paginationRange = getPaginationRange(page, totalPages)

  const renderPaginationControls = () => (
    <div className="flex items-center gap-1">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setPage((prev) => Math.max(prev - 1, 1))}
        disabled={page === 1}
        className="h-8 w-8 p-0"
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>

      {paginationRange.map((item, index) => {
        if (item === "...") {
          return (
            <div
              key={`ellipsis-${index}`}
              className="flex h-8 w-8 items-center justify-center text-muted-foreground"
            >
              <MoreHorizontal className="h-4 w-4" />
            </div>
          )
        }

        const pageNum = item as number
        const isCurrent = pageNum === page

        return (
          <Button
            key={pageNum}
            variant={isCurrent ? "default" : "outline"}
            size="sm"
            onClick={() => setPage(pageNum)}
            className="h-8 w-8 p-0 text-xs font-medium"
          >
            {pageNum}
          </Button>
        )
      })}

      <Button
        variant="outline"
        size="sm"
        onClick={() => setPage((prev) => Math.min(prev + 1, totalPages))}
        disabled={page >= totalPages}
        className="h-8 w-8 p-0"
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  )

  return (
    <div className="flex flex-col gap-4">
      {/* Search Input and Top Pagination */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="relative max-w-md w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            ref={inputRef}
            placeholder="Search ticker or stock name..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="pl-9 bg-background"
          />
        </div>

        <div className="flex items-center justify-end overflow-x-auto py-1">
          {renderPaginationControls()}
        </div>
      </div>

      {/* Loading state or Table */}
      {isLoading ? (
        <PendingItems />
      ) : stocks.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-center py-12 border rounded-lg bg-card">
          <div className="rounded-full bg-muted p-4 mb-4">
            <Search className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">No stocks found</h3>
          <p className="text-muted-foreground text-sm mt-1">
            {searchQuery
              ? `No stocks matching "${searchQuery}"`
              : "Upload an Excel or CSV file to get started"}
          </p>
        </div>
      ) : (
        <>
          <DataTable columns={columns} data={stocks} enableSearch={false} />

          {/* Bottom Pagination */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-t pt-4 text-sm text-muted-foreground">
            <div>
              Showing{" "}
              <span className="font-medium text-foreground">{skip + 1}</span> to{" "}
              <span className="font-medium text-foreground">
                {Math.min(skip + PER_PAGE, totalCount)}
              </span>{" "}
              of{" "}
              <span className="font-medium text-foreground">{totalCount}</span>{" "}
              stocks
            </div>

            <div className="flex items-center justify-end overflow-x-auto w-full sm:w-auto">
              {renderPaginationControls()}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function Stocks() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Stocks</h1>
          <p className="text-muted-foreground">
            Manage and track inventory stock records
          </p>
        </div>
        <UploadStocksModal />
      </div>
      <StocksTableContent />
    </div>
  )
}

export default Stocks