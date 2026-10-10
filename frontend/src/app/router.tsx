import React from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/app-shell";

// Auth features
import { SignInPage } from "@/features/auth/sign-in";
import { SignUpPage } from "@/features/auth/sign-up";
import { ForgotPasswordPage } from "@/features/auth/forgot-password";

// App features
import { DashboardPage } from "@/features/dashboard/dashboard-page";
import { IntakePage } from "@/features/intake/intake-page";
import { RulesPage } from "@/features/rules/rules-page";
import { SchedulePage } from "@/features/schedule/schedule-page";
import { ConflictsPage } from "@/features/conflicts/conflicts-page";
import { ApprovalsPage } from "@/features/approvals/approvals-page";
import { PublishPage } from "@/features/publish/publish-page";
import { ScoreboardPage } from "@/features/scoreboard/scoreboard-page";
import { ChainPage } from "@/features/chain/chain-page";
import { SettingsPage } from "@/features/settings/settings-page";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/app/dashboard" replace />,
  },
  {
    path: "/auth/sign-in",
    element: <SignInPage />,
  },
  {
    path: "/auth/sign-up",
    element: <SignUpPage />,
  },
  {
    path: "/auth/forgot-password",
    element: <ForgotPasswordPage />,
  },
  {
    path: "/app",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <Navigate to="/app/dashboard" replace />,
      },
      {
        path: "dashboard",
        element: <DashboardPage />,
      },
      {
        path: "intake",
        element: <IntakePage />,
      },
      {
        path: "rules",
        element: <RulesPage />,
      },
      {
        path: "schedule",
        element: <SchedulePage />,
      },
      {
        path: "conflicts",
        element: <ConflictsPage />,
      },
      {
        path: "approvals",
        element: <ApprovalsPage />,
      },
      {
        path: "publish",
        element: <PublishPage />,
      },
      {
        path: "scoreboard",
        element: <ScoreboardPage />,
      },
      {
        path: "chain-log",
        element: <ChainPage />,
      },
      {
        path: "settings",
        element: <SettingsPage />,
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/app/dashboard" replace />,
  },
]);
