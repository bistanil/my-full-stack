import { EllipsisVertical } from "lucide-react"
import { useState } from "react"

import type { StockPublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import DeleteStock from "./DeleteStock"
import EditStock from "./EditStock"

interface StockActionsMenuProps {
  stock: StockPublic
}

export const StockActionsMenu = ({ stock }: StockActionsMenuProps) => {
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <EditStock stock={stock} onSuccess={() => setOpen(false)} />
        <DeleteStock id={stock.id} onSuccess={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}