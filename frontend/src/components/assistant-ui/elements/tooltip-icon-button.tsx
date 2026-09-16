/** Adapted from assistant-ui's tooltip-icon-button for the existing Base UI primitives. */
import { forwardRef, type ComponentPropsWithoutRef } from "react";
import type { VariantProps } from "class-variance-authority";
import { buttonVariants } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { ghostButton } from "./surfaces";

export const TooltipIconButton = forwardRef<HTMLButtonElement,
  ComponentPropsWithoutRef<"button"> & VariantProps<typeof buttonVariants> & {
    tooltip: string;
    side?: "top" | "bottom" | "left" | "right";
  }
>(({ tooltip, side = "bottom", variant, size, children, className, ...props }, ref) => (
  <Tooltip>
    <TooltipTrigger
      render={<button
        type="button"
        ref={ref}
        aria-label={tooltip}
        className={cn(
          variant || size ? buttonVariants({ variant: variant ?? "ghost", size: size ?? "icon" }) : undefined,
          "inline-flex size-7 shrink-0 items-center justify-center [&_svg]:size-3.5", ghostButton, className,
        )}
        {...props}
      />}
    >
      {children}
    </TooltipTrigger>
    <TooltipContent side={side}>{tooltip}</TooltipContent>
  </Tooltip>
));
TooltipIconButton.displayName = "TooltipIconButton";
