import React, { useState } from "react";
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
  Shield,
  Activity,
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
    refetchInterval: 10000,
  });

  const navItems = [
    { label: "Dashboard", to: "/app/dashboard", icon: LayoutDashboard },
    { label: "Intake", to: "/app/intake", icon: Inbox },
    { label: "Constraints", to: "/app/rules", icon: Sliders },
    { label: "Schedule", to: "/app/schedule", icon: Calendar },
    { label: "Conflicts", to: "/app/conflicts", icon: AlertTriangle },
    { label: "Approvals", to: "/app/approvals", icon: CheckCheck },
    { label: "Publish & Verify", to: "/app/publish", icon: FileCheck },
    { label: "Scoreboard", to: "/app/scoreboard", icon: BarChart3 },
    { label: "Chain Log", to: "/app/chain-log", icon: Link2 },
  ];

  const pgOk = health?.items?.postgres?.ok ?? false;
  const anvilOk = health?.items?.anvil?.ok ?? false;
  const contractOk = health?.items?.contract?.ok ?? false;
  const dockerOk = health?.items?.docker?.ok ?? false;
  const allOk = pgOk && anvilOk && contractOk && dockerOk;

  return (
    <aside
      className={cn(
        "relative flex flex-col border-r border-border bg-card/90 backdrop-blur-md transition-all duration-200 z-20 select-none",
        isCollapsed ? "w-[68px]" : "w-[250px]"
      )}
    >
      {/* Brand Header */}
      <div className="flex h-14 items-center justify-between px-4 border-b border-border">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="h-7 w-7 rounded-lg bg-foreground text-background flex items-center justify-center font-bold text-xs shrink-0 shadow-sm">
            GC
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <span className="font-semibold text-sm tracking-tight leading-none text-foreground">
                GeCompose
              </span>
              <span className="text-[10px] text-muted-foreground mt-0.5">Constraint Engine</span>
            </div>
          )}
        </div>
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="text-muted-foreground hover:text-foreground p-1 rounded-md hover:bg-muted transition-colors"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 space-y-1 p-2.5 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors",
                isActive
                  ? "bg-foreground text-background shadow-xs font-semibold"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )
            }
          >
            <item.icon size={16} className="shrink-0" />
            {!isCollapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Health status & Settings */}
      <div className="p-3 border-t border-border space-y-2">
        <NavLink
          to="/app/settings"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors",
              isActive
                ? "bg-foreground text-background"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )
          }
        >
          <Settings size={16} className="shrink-0" />
          {!isCollapsed && <span>Settings & Health</span>}
        </NavLink>

        {!isCollapsed ? (
          <div className="p-2.5 rounded-lg border border-border bg-muted/40 text-[11px] space-y-1.5">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="flex items-center gap-1.5 font-medium">
                <Activity size={12} className={allOk ? "text-emerald-500" : "text-amber-500"} />
                Node Services
              </span>
              <span className={cn("text-[10px] font-semibold", allOk ? "text-emerald-600" : "text-amber-600")}>
                {allOk ? "ONLINE" : "ATTN"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-1 text-[10px] text-muted-foreground pt-0.5">
              <span className="flex items-center gap-1">
                <span className={cn("h-1.5 w-1.5 rounded-full", pgOk ? "bg-emerald-500" : "bg-rose-500")} />
                PostgreSQL
              </span>
              <span className="flex items-center gap-1">
                <span className={cn("h-1.5 w-1.5 rounded-full", anvilOk ? "bg-emerald-500" : "bg-rose-500")} />
                Anvil RPC
              </span>
              <span className="flex items-center gap-1">
                <span className={cn("h-1.5 w-1.5 rounded-full", contractOk ? "bg-emerald-500" : "bg-rose-500")} />
                ConsentLedger
              </span>
              <span className="flex items-center gap-1">
                <span className={cn("h-1.5 w-1.5 rounded-full", dockerOk ? "bg-emerald-500" : "bg-rose-500")} />
                Docker SB
              </span>
            </div>
          </div>
        ) : (
          <div className="flex justify-center py-1">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                allOk ? "bg-emerald-500" : "bg-amber-500"
              )}
              title={allOk ? "All node services online" : "Some node services require attention"}
            />
          </div>
        )}
      </div>
    </aside>
  );
}
