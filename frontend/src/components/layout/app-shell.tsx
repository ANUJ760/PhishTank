import React, { useEffect } from "react";
import { Outlet, useLocation, Navigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Navbar } from "./navbar";
import { AmbientBackground } from "../background/ambient-background";
import { pageMotionVariants } from "@/lib/motion";
import { useAuth } from "@/lib/auth-context";

export function AppShell() {
  const { user, isLoading } = useAuth();
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
    <div className="relative flex flex-col h-screen w-screen overflow-hidden bg-black text-zinc-100 antialiased">
      <AmbientBackground />
      <Navbar />
      <main className="flex-1 overflow-y-auto relative z-10">
        <div className="px-6 md:px-10 py-6 md:py-8">
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
        </div>
      </main>
    </div>
  );
}
