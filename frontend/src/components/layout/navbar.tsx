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
  LifeBuoy,
  Activity,
  Cpu,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api-client";
import { useQueryClient } from "@tanstack/react-query";

const primaryNav = [
  { label: "Dashboard", to: "/app/dashboard", icon: LayoutDashboard },
  { label: "Schedule", to: "/app/schedule", icon: Calendar },
  { label: "ReliefOps", to: "/app/reliefops", icon: LifeBuoy },
  { label: "MedOps", to: "/app/medops", icon: Activity },
  { label: "Universal", to: "/app/universal", icon: Cpu },
];

const secondaryNav = [
  { label: "Intake", to: "/app/intake", icon: Inbox },
  { label: "Constraints", to: "/app/rules", icon: Sliders },
  { label: "Conflicts", to: "/app/conflicts", icon: AlertTriangle },
  { label: "Approvals", to: "/app/approvals", icon: CheckCheck },
  { label: "Publish & Verify", to: "/app/publish", icon: FileCheck },
  { label: "Scoreboard", to: "/app/scoreboard", icon: BarChart3 },
  { label: "Audit Ledger", to: "/app/chain-log", icon: ShieldCheck },
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
    <header className="sticky top-0 z-50 w-full border-b border-white/[0.08] bg-[#09090c]/85 backdrop-blur-2xl">
      <div className="mx-auto flex h-13 max-w-screen-2xl items-center justify-between px-5 py-2.5">
        {/* Left: Brand + Primary Nav */}
        <div className="flex items-center gap-7">
          {/* Brand */}
          <NavLink
            to="/app/dashboard"
            className="group flex items-center gap-2.5 text-white font-semibold text-sm tracking-tight select-none"
          >
            <div className="h-7 w-7 rounded-md bg-white text-zinc-950 flex items-center justify-center font-bold text-[11px] shadow-sm shadow-white/20 group-hover:scale-105 transition-transform duration-200">
              GC
            </div>
            <span className="hidden sm:inline font-semibold tracking-tight text-[15px]">GeCompose</span>
          </NavLink>

          {/* Primary nav links */}
          <nav className="hidden md:flex items-center gap-1">
            {primaryNav.map((item) => (
              <NavLink key={item.to} to={item.to} className={navLinkClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Right: Clean Demo Coordinator + Slider Trigger */}
        <div className="flex items-center gap-3">
          {/* User profile pill */}
          {user && (
            <div className="flex items-center gap-2.5 px-2.5 py-1 rounded-md bg-white/[0.03] border border-white/[0.07] hover:border-white/[0.12] transition-colors duration-200">
              <div className="h-6 w-6 rounded-md bg-zinc-800 border border-white/10 text-white font-semibold flex items-center justify-center text-[11px] shadow-inner">
                {user.name.charAt(0)}
              </div>
              <div className="flex flex-col text-left">
                <span className="font-medium text-zinc-200 leading-none text-[12px]">{user.name}</span>
                <span className="text-[10px] text-zinc-500 capitalize leading-tight mt-0.5">{user.role}</span>
              </div>
              <button
                onClick={handleSignOut}
                className="text-zinc-500 hover:text-white p-1 rounded-md hover:bg-white/[0.08] transition-all duration-200 ml-1"
                title="Sign out"
              >
                <LogOut size={13} />
              </button>
            </div>
          )}

          {/* Three Lines Slider Trigger (Drawer Menu) */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className={cn(
              "p-1.5 rounded-md border transition-all duration-200 hover:scale-105 active:scale-95",
              menuOpen
                ? "bg-white/[0.1] text-white border-white/20 shadow-[0_0_15px_rgba(255,255,255,0.08)]"
                : "text-zinc-400 hover:text-white hover:bg-white/[0.06] border-white/[0.08] hover:border-white/15"
            )}
            title="Navigation drawer"
            aria-label="Open menu drawer"
          >
            {menuOpen ? <X size={17} /> : <Menu size={17} />}
          </button>
        </div>
      </div>

      {/* Slide-over Drawer (Three lines slider) */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop overlay */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300"
            onClick={() => setMenuOpen(false)}
          />

          {/* Drawer panel */}
          <div
            ref={menuRef}
            className="relative z-10 w-80 max-w-[85vw] h-full bg-[#0d0d11]/95 backdrop-blur-2xl border-l border-white/[0.1] p-6 flex flex-col justify-between shadow-2xl shadow-black/80 animate-in slide-in-from-right duration-250"
          >
            <div className="space-y-6">
              {/* Drawer header */}
              <div className="flex items-center justify-between pb-4 border-b border-white/[0.08]">
                <div className="flex items-center gap-2">
                  <div className="h-6 w-6 rounded-md bg-white text-zinc-950 flex items-center justify-center font-bold text-[10px]">
                    GC
                  </div>
                  <span className="font-semibold text-white text-sm">GeCompose Navigation</span>
                </div>
                <button
                  onClick={() => setMenuOpen(false)}
                  className="p-1 rounded-md text-zinc-400 hover:text-white hover:bg-white/[0.08] transition-colors"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Mobile primary nav links */}
              <div className="md:hidden space-y-1">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 px-3 pb-1">
                  Primary Views
                </p>
                {primaryNav.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setMenuOpen(false)}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 px-3 py-2 rounded-md text-[13px] font-medium transition-all duration-150",
                        isActive
                          ? "bg-white/[0.1] text-white shadow-sm"
                          : "text-zinc-400 hover:bg-white/[0.05] hover:text-zinc-200"
                      )
                    }
                  >
                    <item.icon size={15} className="shrink-0 opacity-70" />
                    <span>{item.label}</span>
                  </NavLink>
                ))}
              </div>

              {/* Secondary nav links */}
              <div className="space-y-1">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 px-3 pb-1">
                  Workflows & Tools
                </p>
                {secondaryNav.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setMenuOpen(false)}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 px-3 py-2.5 rounded-md text-[13px] font-medium transition-all duration-150",
                        isActive
                          ? "bg-white/[0.1] text-white shadow-sm"
                          : "text-zinc-400 hover:bg-white/[0.05] hover:text-zinc-200 hover:translate-x-0.5"
                      )
                    }
                  >
                    <item.icon size={15} className="shrink-0 opacity-70" />
                    <span>{item.label}</span>
                  </NavLink>
                ))}
              </div>

              {/* Utilities & Demo management tucked neatly in drawer */}
              <div className="pt-2 space-y-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 px-3">
                  Workspace Utilities
                </p>

                <div className="px-3 py-2 rounded-md bg-white/[0.03] border border-white/[0.06] flex items-center justify-between text-xs text-zinc-400">
                  <span className="flex items-center gap-1.5">
                    <Database size={12} className="text-zinc-500" />
                    Active Environment
                  </span>
                  <span className="text-[11px] text-zinc-300 font-medium">Unified Constraint Engine</span>
                </div>

                <button
                  onClick={handleSeedDemo}
                  disabled={isSeeding}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-[12px] font-medium text-zinc-300 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-white/15 transition-all duration-200 disabled:opacity-50"
                >
                  <RefreshCw size={13} className={isSeeding ? "animate-spin" : ""} />
                  <span>{isSeeding ? "Seeding Database..." : "Seed Demo Baseline"}</span>
                </button>
              </div>
            </div>

            {/* Drawer footer */}
            <div className="pt-4 border-t border-white/[0.08] flex items-center justify-between text-xs text-zinc-500">
              <span>GeCompose Engine</span>
              <button
                onClick={() => {
                  setMenuOpen(false);
                  handleSignOut();
                }}
                className="flex items-center gap-1.5 text-zinc-400 hover:text-white transition-colors"
              >
                <LogOut size={13} />
                <span>Sign out</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
