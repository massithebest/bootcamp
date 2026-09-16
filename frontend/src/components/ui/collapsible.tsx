import { forwardRef } from "react"
import { Collapsible as CollapsiblePrimitive } from "@base-ui/react/collapsible"

const Collapsible = forwardRef<HTMLDivElement, CollapsiblePrimitive.Root.Props>(({ ...props }, ref) => {
  return <CollapsiblePrimitive.Root ref={ref} data-slot="collapsible" {...props} />
})
Collapsible.displayName = "Collapsible"

function CollapsibleTrigger({ ...props }: CollapsiblePrimitive.Trigger.Props) {
  return (
    <CollapsiblePrimitive.Trigger data-slot="collapsible-trigger" {...props} />
  )
}

function CollapsibleContent({ ...props }: CollapsiblePrimitive.Panel.Props) {
  return (
    <CollapsiblePrimitive.Panel data-slot="collapsible-content" {...props} />
  )
}

export { Collapsible, CollapsibleTrigger, CollapsibleContent }
