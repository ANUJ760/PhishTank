import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { LogOut, RefreshCw, Database } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TopbarProps {
  darkMode: boolean;
  setDarkMode: (val: boolean) => void;
}

export function Topbar({ darkMode, setDarkMode }: TopbarProps) {
  const { user, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isSeeding, setIsSeeding] = React.useState(false);

  // Derive route title
  const path = location.pathname.replace("/app/", "");
  const titles: Record<string, string> = {
    dashboard: "Operations Dashboard",
    intake: "Constraint Intake",
    rules: "Constraints & Rule Review",
    schedule: "Timetable Schedule Grid",
    conflicts: "Conflict Studio",
    approvals: "On-Chain Multi-Party Approvals",
    publish: "Schedule Publication & Proof Portal",
    scoreboard: "Evaluation Scoreboard",
    "chain-log": "Blockchain Audit Log",
    settings: "System Health & Diagnostics",
  };
  const title = titles[path] || "Workspace";

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

  return (
    <header className="h-14 border-b border-white/[0.08] bg-[#0c0c0f]/80 backdrop-blur-xl px-6 flex items-center justify-between z-10 select-none text-zinc-300">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-white tracking-tight">{title}</h1>
        <span className="text-zinc-600 text-xs">/</span>
        <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/[0.04] border border-white/10 text-[11px] font-medium text-zinc-400">
          <Database size={11} className="text-zinc-300" />
          <span>College Demo v1</span>
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        <Button
          variant="outline"
          size="sm"
          onClick={handleSeedDemo}
          isLoading={isSeeding}
          className="text-xs h-8 rounded-full border-white/10 bg-white/[0.04] text-zinc-300 hover:bg-white/10 hover:text-white gap-1.5"
          title="Seed baseline demo rules and schedule"
        >
          <RefreshCw size={13} className={isSeeding ? "animate-spin" : ""} />
          <span>Seed Demo</span>
        </Button>

        <div className="h-4 w-[1px] bg-white/10 mx-1" />

        {user && (
          <div className="flex items-center gap-2.5 text-xs bg-white/[0.03] border border-white/[0.08] rounded-full px-2.5 py-1">
            <div className="h-6 w-6 rounded-full bg-zinc-800 text-white font-semibold flex items-center justify-center text-[11px]">
              {user.name.charAt(0)}
            </div>
            <div className="hidden sm:flex flex-col text-left">
              <span className="font-medium text-zinc-200 leading-none text-xs">{user.name}</span>
              <span className="text-[10px] text-zinc-400 capitalize mt-0.5">{user.role}</span>
            </div>
            <button
              onClick={handleSignOut}
              className="text-zinc-400 hover:text-white p-1 rounded-full hover:bg-white/10 transition-colors ml-1"
              title="Sign out"
            >
              <LogOut size={13} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
