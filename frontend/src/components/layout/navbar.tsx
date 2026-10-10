import React, { useState, useRef, useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";
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
  Menu,
  X,
  LogOut,
  RefreshCw,
  Database,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api-client";
import { useQueryClient } from "@tanstack/react-query";

const primaryNav = [
  { label: "Dashboard", to: "/app/dashboard", icon: LayoutDashboard },
  { label: "Intake", to: "/app/intake", icon: Inbox },
  { label: "Constraints", to: "/app/rules", icon: Sliders },
  { label: "Schedule", to: "/app/schedule", icon: Calendar },
  { label: "Conflicts", to: "/app/conflicts", icon: AlertTriangle },
];

const secondaryNav = [
  { label: "Approvals", to: "/app/approvals", icon: CheckCheck },
  { label: "Publish & Verify", to: "/app/publish", icon: FileCheck },
  { label: "Scoreboard", to: "/app/scoreboard", icon: BarChart3 },
  { label: "Chain Log", to: "/app/chain-log", icon: Link2 },
  { label: "Settings", to: "/app/settings", icon: Settings },
];

export function Navbar() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [menuOpen, setMenuOpen] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    if (menuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [menuOpen]);

  const handleSeedDemo = async () => {
    setIsSeeding(true);
    try {
      await api.demo.seed();
      queryClient.invalidateQueries();
    } finally {
      setIsSeeding(false);
    }
  };

  const handleSignOut = async () => {
    await signOut();
    navigate("/auth/sign-in");
  };

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      "relative px-3 py-1.5 text-[13px] font-medium transition-all duration-200 rounded-md",
      isActive
        ? "text-white bg-white/[0.08] backdrop-blur-sm"
        : "text-zinc-400 hover:text-zinc-100 hover:bg-white/[0.04]"
    );

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/[0.07] bg-[#0a0a0c]/90 backdrop-blur-xl">
      <div className="mx-auto flex h-12 max-w-screen-2xl items-center justify-between px-5">
        {/* Left: Brand + Primary Nav */}
        <div className="flex items-center gap-6">
          {/* Brand */}
          <NavLink
            to="/app/dashboard"
            className="flex items-center gap-2 text-white font-semibold text-sm tracking-tight select-none mr-1"
          >
            <div className="h-6 w-6 rounded-md bg-white text-zinc-950 flex items-center justify-center font-bold text-[10px] shrink-0">
              GC
            </div>
            <span className="hidden sm:inline">GeCompose</span>
          </NavLink>

          {/* Primary nav links */}
          <nav className="hidden md:flex items-center gap-0.5">
            {primaryNav.map((item) => (
              <NavLink key={item.to} to={item.to} className={navLinkClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Right: Actions + Hamburger */}
        <div className="flex items-center gap-2">
          {/* Seed Demo button */}
          <button
            onClick={handleSeedDemo}
            disabled={isSeeding}
            className="hidden sm:inline-flex items-center gap-1.5 h-7 px-3 text-[12px] font-medium text-zinc-400 hover:text-white bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] rounded-md transition-all duration-200 disabled:opacity-50"
            title="Seed baseline demo rules and schedule"
          >
            <RefreshCw size={12} className={isSeeding ? "animate-spin" : ""} />
            <span>Seed Demo</span>
          </button>

          {/* Env tag */}
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-zinc-500 bg-white/[0.02] border border-white/[0.06] rounded-md">
            <Database size={10} />
            <span>College Demo v1</span>
          </div>

          {/* User pill */}
          {user && (
            <div className="hidden sm:flex items-center gap-2 text-xs pl-2">
              <div className="h-6 w-6 rounded-md bg-zinc-800 text-white font-semibold flex items-center justify-center text-[11px]">
                {user.name.charAt(0)}
              </div>
              <div className="flex flex-col text-left">
                <span className="font-medium text-zinc-300 leading-none text-[12px]">{user.name}</span>
                <span className="text-[10px] text-zinc-500 capitalize">{user.role}</span>
              </div>
              <button
                onClick={handleSignOut}
                className="text-zinc-500 hover:text-white p-1 rounded-md hover:bg-white/[0.06] transition-all duration-200 ml-0.5"
                title="Sign out"
              >
                <LogOut size={13} />
              </button>
            </div>
          )}

          {/* Hamburger menu trigger */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className={cn(
                "p-1.5 rounded-md transition-all duration-200",
                menuOpen
                  ? "bg-white/[0.08] text-white"
                  : "text-zinc-400 hover:text-white hover:bg-white/[0.05]"
              )}
              title="More navigation"
            >
              {menuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>

            {/* Dropdown panel */}
            {menuOpen && (
              <div className="absolute right-0 top-[calc(100%+8px)] w-56 p-2 rounded-lg bg-[#111114]/95 backdrop-blur-2xl border border-white/[0.08] shadow-2xl shadow-black/40 z-50">
                {/* Show primary nav on mobile */}
                <div className="md:hidden space-y-0.5 pb-2 mb-2 border-b border-white/[0.06]">
                  {primaryNav.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={() => setMenuOpen(false)}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] font-medium transition-all duration-150",
                          isActive
                            ? "bg-white/[0.08] text-white"
                            : "text-zinc-400 hover:bg-white/[0.05] hover:text-zinc-200"
                        )
                      }
                    >
                      <item.icon size={15} className="shrink-0 opacity-60" />
                      <span>{item.label}</span>
                    </NavLink>
                  ))}
                </div>

                {/* Secondary nav always visible */}
                <div className="space-y-0.5">
                  {secondaryNav.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={() => setMenuOpen(false)}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] font-medium transition-all duration-150",
                          isActive
                            ? "bg-white/[0.08] text-white"
                            : "text-zinc-400 hover:bg-white/[0.05] hover:text-zinc-200"
                        )
                      }
                    >
                      <item.icon size={15} className="shrink-0 opacity-60" />
                      <span>{item.label}</span>
                    </NavLink>
                  ))}
                </div>

                {/* Mobile user actions */}
                {user && (
                  <div className="sm:hidden pt-2 mt-2 border-t border-white/[0.06] space-y-0.5">
                    <button
                      onClick={handleSeedDemo}
                      disabled={isSeeding}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] font-medium text-zinc-400 hover:bg-white/[0.05] hover:text-zinc-200 transition-all disabled:opacity-50"
                    >
                      <RefreshCw size={15} className={cn("shrink-0 opacity-60", isSeeding && "animate-spin")} />
                      <span>Seed Demo</span>
                    </button>
                    <button
                      onClick={() => {
                        setMenuOpen(false);
                        handleSignOut();
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] font-medium text-zinc-400 hover:bg-white/[0.05] hover:text-zinc-200 transition-all"
                    >
                      <LogOut size={15} className="shrink-0 opacity-60" />
                      <span>Sign out</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
