import React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sliders,
  AlertTriangle,
  Calendar,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Link2,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { motion } from "framer-motion";
import { cardMotionVariants } from "@/lib/motion";

export function DashboardPage() {
  const { data: summary, isLoading: isSummaryLoading } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: api.dashboardSummary,
    refetchInterval: 6000,
  });

  const { data: schedule } = useQuery({
    queryKey: ["latest-schedule"],
    queryFn: api.schedules.latest,
  });

  const { data: eventsData } = useQuery({
    queryKey: ["chain-events"],
    queryFn: api.chainEvents,
  });

  const recentEvents = (eventsData?.events || []).slice(-5).reverse();

  return (
    <div className="space-y-6 text-left">
      {/* Page Title & Hero */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Operational Overview</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time status of university scheduling constraints, solver status, and consensus.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/app/schedule">
            <Button size="sm" className="gap-1.5 text-xs h-8">
              <span>View Timetable</span>
              <ArrowRight size={13} />
            </Button>
          </Link>
        </div>
      </div>

      {/* 4 Metric KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div custom={0} variants={cardMotionVariants} initial="initial" animate="animate">
          <Card className="hover:border-border/80 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle>Confirmed Constraints</CardTitle>
              <Sliders size={16} className="text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold tracking-tight text-foreground">
                {isSummaryLoading ? "—" : summary?.confirmed_rules_count ?? 0}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1 flex items-center gap-1.5">
                <span className="text-primary font-medium">{summary?.draft_rules_count ?? 0}</span> draft rules pending review
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div custom={1} variants={cardMotionVariants} initial="initial" animate="animate">
          <Card className="hover:border-border/80 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle>Conflict Status</CardTitle>
              <AlertTriangle size={16} className={summary?.conflict_active ? "text-rose-500" : "text-emerald-500"} />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <div className="text-2xl font-bold tracking-tight text-foreground">
                  {summary?.conflict_active ? "Infeasible" : "Feasible"}
                </div>
                {summary?.conflict_active ? (
                  <Badge variant="destructive">Conflict Core</Badge>
                ) : (
                  <Badge variant="success">Satisfied</Badge>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                {summary?.conflict_active
                  ? `Rules: ${summary.conflict_rule_ids.join(", ")}`
                  : "All constraints mathematically satisfied"}
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div custom={2} variants={cardMotionVariants} initial="initial" animate="animate">
          <Card className="hover:border-border/80 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle>Scheduled Sessions</CardTitle>
              <Calendar size={16} className="text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold tracking-tight text-foreground">
                {isSummaryLoading ? "—" : summary?.scheduled_sessions_count ?? 0}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                Across 5 days &bull; 6 daily slots
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div custom={3} variants={cardMotionVariants} initial="initial" animate="animate">
          <Card className="hover:border-border/80 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle>Published Version</CardTitle>
              <ShieldCheck size={16} className="text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold tracking-tight text-foreground">
                {summary?.published_version ? `v${summary.published_version}` : "v1"}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1 truncate font-mono">
                Anchored on Anvil Ethereum
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Main Grid: Workflow & Recent Chain Events */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Schedule Snapshot & Workflow */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-foreground">Current Active Timetable</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Verified schedule placements generated by Google OR-Tools CP-SAT.
                </p>
              </div>
              <Link to="/app/schedule">
                <Button variant="ghost" size="sm" className="text-xs h-7 gap-1">
                  Full Grid <ArrowRight size={12} />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {schedule?.placements && schedule.placements.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-border text-muted-foreground">
                        <th className="py-2 px-3 font-medium">Session ID</th>
                        <th className="py-2 px-3 font-medium">Teacher</th>
                        <th className="py-2 px-3 font-medium">Room</th>
                        <th className="py-2 px-3 font-medium">Day</th>
                        <th className="py-2 px-3 font-medium">Slot</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {schedule.placements.slice(0, 6).map((p) => {
                        const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri"];
                        const slotTimes = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00"];
                        return (
                          <tr key={p.session_id} className="hover:bg-muted/40 transition-colors">
                            <td className="py-2 px-3 font-semibold text-foreground">{p.session_id}</td>
                            <td className="py-2 px-3 text-muted-foreground">{p.teacher}</td>
                            <td className="py-2 px-3 text-muted-foreground">{p.room}</td>
                            <td className="py-2 px-3 text-muted-foreground">{dayNames[p.day] || p.day}</td>
                            <td className="py-2 px-3 text-muted-foreground">{slotTimes[p.slot] || p.slot}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-muted-foreground">
                  No active schedule available. Click &quot;Seed Demo&quot; to populate.
                </div>
              )}
            </CardContent>
          </Card>

          {/* Demonstration Quick Workflow */}
          <Card className="bg-muted/20">
            <CardHeader>
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                <Sparkles size={14} className="text-primary" />
                Demonstration Verification Workflow
              </h3>
              <p className="text-xs text-muted-foreground">
                Follow these steps to exercise the full end-to-end multi-party constraint resolution cycle:
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <Link
                  to="/app/conflicts"
                  className="p-3 rounded-lg border border-border bg-card hover:border-primary/40 transition-colors block"
                >
                  <span className="font-semibold text-foreground flex items-center gap-1.5 mb-1">
                    1. Inject Clash (R3)
                  </span>
                  <p className="text-muted-foreground text-[11px]">
                    Register Prof. Rao&apos;s unavailability on Monday to create the {`{R1, R2, R3}`} conflict.
                  </p>
                </Link>

                <Link
                  to="/app/approvals"
                  className="p-3 rounded-lg border border-border bg-card hover:border-primary/40 transition-colors block"
                >
                  <span className="font-semibold text-foreground flex items-center gap-1.5 mb-1">
                    2. Test On-Chain Consent
                  </span>
                  <p className="text-muted-foreground text-[11px]">
                    Attempt non-owner approval (reverts), then approve with the authorized rule owner.
                  </p>
                </Link>

                <Link
                  to="/app/publish"
                  className="p-3 rounded-lg border border-border bg-card hover:border-primary/40 transition-colors block"
                >
                  <span className="font-semibold text-foreground flex items-center gap-1.5 mb-1">
                    3. Publish & Tamper Test
                  </span>
                  <p className="text-muted-foreground text-[11px]">
                    Anchor v2 on Ethereum, export files, and test tamper detection.
                  </p>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Col: Recent Blockchain Events */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <Link2 size={14} className="text-primary" />
                  Recent On-Chain Activity
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">ConsentLedger contract events</p>
              </div>
              <Link to="/app/chain-log">
                <Button variant="ghost" size="sm" className="text-xs h-7">
                  All <ArrowRight size={12} />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {recentEvents.length > 0 ? (
                <div className="space-y-3">
                  {recentEvents.map((ev, i) => (
                    <div
                      key={i}
                      className="p-2.5 rounded-lg border border-border bg-muted/30 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-foreground text-[11px]">{ev.event}</span>
                        <span className="text-[10px] text-muted-foreground font-mono">Block #{ev.block}</span>
                      </div>
                      <div className="text-[10px] text-muted-foreground truncate font-mono">
                        {ev.args?.ruleHash || ev.args?.scheduleHash || JSON.stringify(ev.args)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-muted-foreground">
                  No blockchain transactions logged yet.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
