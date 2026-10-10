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
      default: "bg-white text-zinc-950 hover:bg-zinc-200 font-medium shadow-sm active:scale-[0.99]",
      secondary: "bg-zinc-800/80 text-zinc-200 hover:bg-zinc-700/80 border border-white/10 active:scale-[0.99]",
      outline: "border border-white/15 bg-transparent hover:bg-white/5 text-zinc-300 active:scale-[0.99]",
      ghost: "text-zinc-400 hover:text-zinc-100 hover:bg-white/5",
      destructive: "bg-zinc-900 border border-white/10 text-zinc-300 hover:bg-zinc-800",
      link: "text-zinc-300 underline-offset-4 hover:underline hover:text-white",
    };

    const sizes = {
      default: "h-9 px-4 py-2 text-sm rounded-xl",
      sm: "h-8 px-3 text-xs rounded-lg",
      lg: "h-11 px-6 text-sm rounded-2xl",
      icon: "h-9 w-9 rounded-xl",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          "inline-flex items-center justify-center gap-2 font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/20 disabled:pointer-events-none disabled:opacity-50 select-none",
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
