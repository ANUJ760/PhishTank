import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "secondary" | "outline" | "ghost" | "destructive" | "link";
  size?: "default" | "sm" | "lg" | "icon";
  isLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", isLoading, children, disabled, ...props }, ref) => {
    const variants = {
      default: "bg-white text-zinc-950 font-medium shadow-sm hover:bg-zinc-100 hover:shadow-[0_0_20px_rgba(255,255,255,0.2)] hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]",
      secondary: "bg-white/[0.05] text-zinc-200 border border-white/10 hover:bg-white/[0.09] hover:border-white/20 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/40 active:scale-[0.98]",
      outline: "border border-white/12 bg-transparent text-zinc-300 hover:bg-white/[0.06] hover:border-white/25 hover:text-white hover:-translate-y-0.5 active:scale-[0.98]",
      ghost: "text-zinc-400 hover:text-zinc-100 hover:bg-white/[0.06] active:scale-[0.98]",
      destructive: "bg-red-950/40 border border-red-500/20 text-red-300 hover:bg-red-900/40 hover:border-red-500/40 active:scale-[0.98]",
      link: "text-zinc-300 underline-offset-4 hover:underline hover:text-white",
    };

    const sizes = {
      default: "h-9 px-4 py-2 text-sm rounded-md",
      sm: "h-8 px-3 text-xs rounded-md",
      lg: "h-11 px-6 text-sm rounded-md",
      icon: "h-9 w-9 rounded-md",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          "inline-flex items-center justify-center gap-2 font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/20 disabled:pointer-events-none disabled:opacity-50 select-none",
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {isLoading && (
          <svg className="animate-spin -ml-1 mr-2 h-3.5 w-3.5 text-current" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button };
