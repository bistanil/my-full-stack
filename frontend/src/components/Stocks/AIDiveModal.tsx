import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { useMutation } from "@tanstack/react-query"
import { Sparkles, FileSpreadsheet, UploadCloud } from "lucide-react"

import { OpenAPI } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"

interface AIDiveModalProps {
  isOpen: boolean
  onClose: () => void
  stockSymbol?: string
}

export function AIDiveModal({ isOpen, onClose, stockSymbol }: AIDiveModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const navigate = useNavigate()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      const token = localStorage.getItem("access_token")
      const baseUrl = OpenAPI.BASE || ""

      const response = await fetch(`${baseUrl}/api/v1/stocks/analyze-excel`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => null)
        throw new Error(errorData?.detail || "Failed to process stock analysis.")
      }

      return await response.json()
    },
    onSuccess: (data) => {
      showSuccessToast("AI Analysis completed!")
      onClose()

      // Navigate to Stock Detail Page passing the payload in router state
      // Option A: Cast 'to' path as any
navigate({
  to: "/stocks/$symbol" as any,
  params: { symbol: stockSymbol || data.parsed_metrics.company_name } as any,
  state: { stockData: data } as any,
})
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to execute AI analysis.")
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-amber-500" />
            AI Dive Deep Analysis
          </DialogTitle>
          <DialogDescription>
            Upload the Screener.in Excel file for <span className="font-semibold text-foreground">{stockSymbol}</span> to generate fundamental insights and buy targets.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center justify-center border-2 border-dashed border-muted-foreground/30 rounded-xl p-6 bg-muted/20 hover:bg-muted/30 transition-colors relative cursor-pointer group mt-2">
          <input
            type="file"
            accept=".xlsx,.xls"
            className="absolute inset-0 opacity-0 cursor-pointer"
            onChange={(e) => e.target.files?.[0] && setSelectedFile(e.target.files[0])}
            disabled={mutation.isPending}
          />

          {selectedFile ? (
            <div className="flex flex-col items-center text-center gap-2">
              <FileSpreadsheet className="h-10 w-10 text-emerald-500" />
              <p className="text-sm font-medium text-foreground">{selectedFile.name}</p>
              <p className="text-xs text-muted-foreground">({(selectedFile.size / 1024).toFixed(1)} KB)</p>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center gap-2">
              <UploadCloud className="h-10 w-10 text-muted-foreground group-hover:text-primary transition-colors" />
              <p className="text-sm text-foreground font-medium">Click or drag Screener Excel file</p>
              <p className="text-xs text-muted-foreground">Supports .XLSX or .XLS format</p>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 mt-4">
          <Button variant="ghost" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <LoadingButton
            onClick={() => selectedFile && mutation.mutate(selectedFile)}
            loading={mutation.isPending}
            disabled={!selectedFile}
            className="bg-amber-600 hover:bg-amber-700 text-white gap-2"
          >
            <Sparkles className="h-4 w-4" />
            Analyze & View Details
          </LoadingButton>
        </div>
      </DialogContent>
    </Dialog>
  )
}