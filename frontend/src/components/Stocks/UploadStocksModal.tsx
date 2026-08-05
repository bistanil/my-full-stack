import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { FileSpreadsheet, UploadCloud } from "lucide-react"
import { useState } from "react"

import { OpenAPI } from "@/client" // Imports base URL configuration from generated client
import { Button } from "@/components/ui/button.tsx"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog.tsx"
import { LoadingButton } from "@/components/ui/loading-button.tsx"
import useCustomToast from "@/hooks/useCustomToast.ts"

interface UploadStocksModalProps {
  onSuccess?: () => void
}

const UploadStocksModal = ({ onSuccess }: UploadStocksModalProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append("file", file)

      const token = localStorage.getItem("access_token")

      // Construct endpoint using configured base URL (handles Docker/Vite ports safely)
      const baseUrl = OpenAPI.BASE || ""
      const endpoint = `${baseUrl}/api/v1/stocks/upload-excel`

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      })

      // Safe JSON parsing check
      const contentType = response.headers.get("content-type")
      const isJson = contentType && contentType.includes("application/json")

      if (!response.ok) {
        if (isJson) {
          const errorData = await response.json()
          throw new Error(errorData.detail || "Error encountered uploading file.")
        } else {
          // Captures HTML 404 / 502 error pages without crashing JSON parser
          throw new Error(`Server returned HTTP ${response.status} (${response.statusText}). Endpoint path may not exist on backend.`)
        }
      }

      return isJson ? await response.json() : {}
    },
    onSuccess: (data: any) => {
      showSuccessToast(data?.message || "Stocks spreadsheet processed efficiently!")
      setSelectedFile(null)
      setIsOpen(false)

      queryClient.invalidateQueries({ queryKey: ["stocks"] })

      if (onSuccess) onSuccess()

      navigate({ to: "/stocks" })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed execution file upload.")
    },
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0])
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="gap-2 border-dashed border-primary/40 hover:border-primary">
          <UploadCloud className="h-4 w-4" />
          Upload Excel
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Bulk Import Stocks</DialogTitle>
          <DialogDescription>
            Select or drag your structured Google Sheets or Excel document directly below.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center justify-center border-2 border-dashed border-muted-foreground/30 rounded-xl p-6 bg-muted/20 hover:bg-muted/30 transition-colors relative cursor-pointer group mt-2">
          <input
            type="file"
            accept=".xlsx,.xls,.csv"
            className="absolute inset-0 opacity-0 cursor-pointer"
            onChange={handleFileChange}
            disabled={mutation.isPending}
          />

          {selectedFile ? (
            <div className="flex flex-col items-center text-center gap-2">
              <FileSpreadsheet className="h-12 w-12 text-emerald-500" />
              <p className="text-sm font-medium text-foreground">{selectedFile.name}</p>
              <p className="text-xs text-muted-foreground">({(selectedFile.size / 1024).toFixed(1)} KB)</p>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center gap-2">
              <UploadCloud className="h-12 w-12 text-muted-foreground group-hover:text-primary transition-colors" />
              <p className="text-sm text-foreground font-medium">Click or drag data file here</p>
              <p className="text-xs text-muted-foreground">Supports .XLSX, .XLS, or plain .CSV file types</p>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 mt-4">
          <Button
            variant="ghost"
            onClick={() => { setSelectedFile(null); setIsOpen(false); }}
            disabled={mutation.isPending}
          >
            Cancel
          </Button>
          <LoadingButton
            onClick={() => selectedFile && mutation.mutate(selectedFile)}
            loading={mutation.isPending}
            disabled={!selectedFile}
          >
            Process & Import
          </LoadingButton>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default UploadStocksModal