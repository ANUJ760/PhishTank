import React, { useState, useEffect } from "react";
import { Outlet, useLocation, Navigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { AmbientBackground } from "../background/ambient-background";
import { pageMotionVariants } from "@/lib/motion";
import { useAuth } from "@/lib/auth-context";

export function AppShell() {
  const { user, isLoading } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const location = useLocation();

  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-black text-zinc-400 text-sm">
        <div className="flex items-center gap-2">
          <span>Authenticating session...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/auth/sign-in" replace state={{ from: location }} />;
  }

  return (
    <div className="relative flex h-screen w-screen overflow-hidden bg-black text-zinc-100 antialiased">
      <AmbientBackground />
      <Sidebar isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />
      <div className="flex flex-1 flex-col overflow-hidden relative z-10">
        <Topbar darkMode={true} setDarkMode={() => {}} />
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              variants={pageMotionVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              className="mx-auto max-w-7xl"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
