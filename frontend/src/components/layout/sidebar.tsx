import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Inbox,
  Sliders,
  Calendar,
  AlertTriangle,
  CheckCheck,
  FileCheck,
  BarChart3,
  Link2,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

interface SidebarProps {
  isCollapsed: boolean;
  setIsCollapsed: (val: boolean) => void;
}

export function Sidebar({ isCollapsed, setIsCollapsed }: SidebarProps) {
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 15000,
  });

  const navItems = [
    { label: "Dashboard", to: "/app/dashboard", icon: LayoutDashboard },
    { label: "Gemma AI", to: "/app/chat", icon: Sparkles },
    { label: "Intake", to: "/app/intake", icon: Inbox },
    { label: "Constraints", to: "/app/rules", icon: Sliders },
    { label: "Schedule", to: "/app/schedule", icon: Calendar },
    { label: "Conflicts", to: "/app/conflicts", icon: AlertTriangle },
    { label: "Approvals", to: "/app/approvals", icon: CheckCheck },
    { label: "Publish & Verify", to: "/app/publish", icon: FileCheck },
    { label: "Scoreboard", to: "/app/scoreboard", icon: BarChart3 },
    { label: "Audit Ledger", to: "/app/chain-log", icon: Link2 },
  ];

  return (
    <aside
      className={cn(
        "relative flex flex-col border-r border-white/[0.08] bg-[#0c0c0f]/80 backdrop-blur-2xl transition-all duration-200 z-20 select-none text-zinc-300",
        isCollapsed ? "w-[68px]" : "w-[240px]"
      )}
    >
      {/* Brand Header */}
      <div className="flex h-14 items-center justify-between px-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="h-7 w-7 rounded-xl bg-white text-zinc-950 flex items-center justify-center font-bold text-xs shrink-0 shadow-sm">
            GC
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <span className="font-semibold text-sm tracking-tight leading-none text-white">
                GeCompose
              </span>
              <span className="text-[10px] text-zinc-400 mt-0.5">Constraint Engine</span>
            </div>
          )}
        </div>
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="text-zinc-400 hover:text-white p-1 rounded-lg hover:bg-white/5 transition-colors"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 space-y-1 p-3 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all",
                isActive
                  ? "bg-white/10 text-white font-medium border border-white/5 shadow-xs"
                  : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"
              )
            }
          >
            <item.icon size={16} className="shrink-0" />
            {!isCollapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Clean Status & Settings Footer (No blinking, No loud green/red dots) */}
      <div className="p-3 border-t border-white/[0.06] space-y-2">
        <NavLink
          to="/app/settings"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all",
              isActive
                ? "bg-white/10 text-white border border-white/5"
                : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"
            )
          }
        >
          <Settings size={16} className="shrink-0" />
          {!isCollapsed && <span>Settings & Health</span>}
        </NavLink>

        {!isCollapsed && (
          <div className="px-3 py-2 rounded-xl bg-white/[0.02] border border-white/[0.04] text-[11px] text-zinc-400 flex items-center justify-between">
            <span className="text-zinc-400 font-mono text-[10px]">Local Cluster</span>
            <span className="text-zinc-300 font-medium text-[10px]">Active</span>
          </div>
        )}
      </div>
    </aside>
  );
}
