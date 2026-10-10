import React from "react";
import { AmbientBackground } from "@/components/background/ambient-background";

export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen w-screen flex flex-col justify-center items-center p-4 bg-background text-foreground overflow-hidden">
      <AmbientBackground />
      <div className="w-full max-w-[420px] z-10">
        <div className="flex items-center justify-center gap-2.5 mb-8 select-none">
          <div className="h-9 w-9 rounded-xl bg-foreground text-background flex items-center justify-center font-bold text-sm shadow-md">
            GC
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-lg tracking-tight text-foreground leading-none">
              GeCompose
            </span>
            <span className="text-xs text-muted-foreground mt-0.5">Constraint Engine</span>
          </div>
        </div>
        <div className="rounded-2xl border border-border bg-card/90 backdrop-blur-xl p-8 shadow-sm">
          {children}
        </div>
        <div className="mt-8 text-center text-xs text-muted-foreground">
          Enterprise Timetable Synthesis &bull; Local Anvil Consensus
        </div>
      </div>
    </div>
  );
}
