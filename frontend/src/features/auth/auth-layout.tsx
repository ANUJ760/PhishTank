import React from "react";
import { AmbientBackground } from "@/components/background/ambient-background";

export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen w-screen flex flex-col justify-center items-center p-4 bg-black text-white overflow-hidden">
      <AmbientBackground />
      <div className="w-full max-w-[420px] z-10">
        <div className="flex items-center justify-center gap-3 mb-8 select-none">
          <div className="h-10 w-10 flex items-center justify-center drop-shadow-[0_0_12px_rgba(52,211,153,0.35)]">
            <img src="/logo-mark.svg" alt="GeCompose Logo" className="h-10 w-10 object-contain" />
          </div>
          <div className="flex flex-col text-left">
            <span className="font-semibold text-xl tracking-tight text-white leading-none">
              GeCompose
            </span>
            <span className="text-xs text-zinc-400 mt-1">Constraint Engine</span>
          </div>
        </div>
        <div className="glass-box p-8 shadow-2xl">
          {children}
        </div>
        <div className="mt-8 text-center text-xs text-zinc-500">
          Enterprise Timetable & Resource Synthesis &bull; Cryptographic Audit Ledger
        </div>
      </div>
    </div>
  );
}
