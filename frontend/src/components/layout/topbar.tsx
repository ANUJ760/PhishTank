import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { LogOut, RefreshCw, Sun, Moon, Database } from "lucide-react";
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
    <header className="h-14 border-b border-border bg-card/80 backdrop-blur-md px-6 flex items-center justify-between z-10 select-none">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-foreground tracking-tight">{title}</h1>
        <span className="text-muted-foreground/40 text-xs">/</span>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-muted border border-border text-[11px] font-medium text-muted-foreground">
          <Database size={11} className="text-primary" />
          <span>College Demo v1</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleSeedDemo}
          isLoading={isSeeding}
          className="text-xs h-8 gap-1.5"
          title="Seed baseline demo rules and schedule"
        >
          <RefreshCw size={13} className={isSeeding ? "animate-spin" : ""} />
          <span>Seed Demo</span>
        </Button>

        <button
          onClick={() => setDarkMode(!darkMode)}
          className="h-8 w-8 rounded-lg border border-border flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
        >
          {darkMode ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        <div className="h-4 w-[1px] bg-border mx-1" />

        {user && (
          <div className="flex items-center gap-2 text-xs">
            <div className="h-7 w-7 rounded-full bg-primary/10 text-primary font-semibold flex items-center justify-center border border-primary/20">
              {user.name.charAt(0)}
            </div>
            <div className="hidden sm:flex flex-col text-left">
              <span className="font-medium text-foreground leading-none">{user.name}</span>
              <span className="text-[10px] text-muted-foreground capitalize mt-0.5">{user.role}</span>
            </div>
            <button
              onClick={handleSignOut}
              className="text-muted-foreground hover:text-destructive p-1.5 rounded-md hover:bg-muted transition-colors ml-1"
              title="Sign out"
            >
              <LogOut size={15} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
