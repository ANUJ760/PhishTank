import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "success" | "warning" | "destructive";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "bg-zinc-800/90 text-zinc-200 border border-white/10",
    secondary: "bg-zinc-900/80 text-zinc-400 border border-white/5",
    outline: "text-zinc-300 border border-white/15 bg-transparent",
    success: "bg-zinc-800/80 text-zinc-300 border border-white/10",
    warning: "bg-zinc-800/80 text-zinc-300 border border-white/10",
    destructive: "bg-zinc-800/80 text-zinc-300 border border-white/10",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-tight transition-colors focus:outline-none",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
