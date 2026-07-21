import type { ColumnDef } from "@tanstack/react-table"

import type { ItemPublic } from "@/client"
import { ItemActionsMenu } from "./ItemActionsMenu"

export const columns: ColumnDef<ItemPublic>[] = [
  {
    accessorKey: "title",
    header: "Item Details", // Combines them beautifully under a single cleaner header
    cell: ({ row }) => {
      const title = row.original.title
      const description = row.original.description

      return (
        <div className="flex flex-col gap-1.5 py-1">
          {/* Title rendered on top */}
          <span className="font-semibold text-base text-foreground block">
            {title}
          </span>

          {/* Rich text description safely parsed and rendered right below it */}
          {description ? (
            <div
              className="text-sm text-muted-foreground max-w-2xl rich-text-preview"
              dangerouslySetInnerHTML={{ __html: description }}
            />
          ) : (
            <span className="text-sm italic text-muted-foreground/60">
              No description
            </span>
          )}
        </div>
      )
    },
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end items-center h-full">
        <ItemActionsMenu item={row.original} />
      </div>
    ),
  },
]