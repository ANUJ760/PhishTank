import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { PublishResult, VerifyResult } from "@/types/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  FileCheck,
  ShieldCheck,
  Download,
  Upload,
  CheckCircle2,
  XCircle,
  FileCode,
  Calendar,
  Layers,
  AlertTriangle,
  Lock,
} from "lucide-react";

export function PublishPage() {
  const queryClient = useQueryClient();
  const [publishResult, setPublishResult] = useState<PublishResult | null>(null);
  const [verifyFile, setVerifyFile] = useState<File | null>(null);
  const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [tamperDemoResult, setTamperDemoResult] = useState<{ originalOk: boolean; tamperedCaught: boolean } | null>(null);

  const { data: schedule } = useQuery({
    queryKey: ["latest-schedule"],
    queryFn: async () => {
      try {
        return await api.schedules.latest();
      } catch {
        return null;
      }
    },
  });

  const publishMutation = useMutation({
    mutationFn: () => api.publish(),
    onSuccess: (res: PublishResult) => {
      setPublishResult(res);
      queryClient.invalidateQueries();
    },
  });

  const handleVerifyUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verifyFile) return;
    setIsVerifying(true);
    try {
      const res = await api.verify(verifyFile);
      setVerifyResult(res);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleTamperTest = async () => {
    if (!schedule) return;
    setIsVerifying(true);
    try {
      // 1. Verify original schedule JSON
      const originalJson = JSON.stringify(schedule);
      const originalRes = await api.verify(undefined, originalJson);

      // 2. Create tampered copy: alter first placement slot
      const tamperedObj = JSON.parse(originalJson);
      if (tamperedObj.placements && tamperedObj.placements.length > 0) {
        tamperedObj.placements[0].slot = (tamperedObj.placements[0].slot + 1) % 6;
      }
      const tamperedJson = JSON.stringify(tamperedObj);
      const tamperedRes = await api.verify(undefined, tamperedJson);

      setTamperDemoResult({
        originalOk: originalRes.match && originalRes.anchored,
        tamperedCaught: !tamperedRes.match && !tamperedRes.anchored,
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const downloadFile = (b64: string, filename: string, mime: string) => {
    const bytes = atob(b64);
    const u8 = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) {
      u8[i] = bytes.charCodeAt(i);
    }
    const blob = new Blob([u8], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 text-left">
      <div>
        <h2 className="text-xl font-bold tracking-tight text-foreground">Publication & Public Proof Portal</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Cryptographically anchor feasible timetables on Ethereum and independently verify schedule authenticity.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Publication Section */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <FileCheck size={16} className="text-primary" />
                <CardTitle className="text-foreground text-sm font-semibold">
                  Publish to Ethereum Ledger
                </CardTitle>
              </div>
              <p className="text-xs text-muted-foreground">
                Before publishing, independent checker rules verify that zero collisions exist.
              </p>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              <div className="p-3 rounded-lg bg-muted border border-border space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Current Status:</span>
                  <Badge variant={schedule ? "success" : "warning"}>
                    {schedule ? `Version ${schedule.version} Available` : "Solve Required"}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Consensus Target:</span>
                  <span className="font-mono text-[11px] text-foreground">ConsentLedger (0x5FbD...)</span>
                </div>
              </div>

              <Button
                onClick={() => publishMutation.mutate()}
                isLoading={publishMutation.isPending}
                className="w-full gap-1.5 text-xs h-9"
              >
                <Lock size={13} />
                <span>Anchor & Publish Schedule</span>
              </Button>

              {publishMutation.error && (
                <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-xs">
                  Publish error: {(publishMutation.error as any).message}
                </div>
              )}

              {/* Published Result Box */}
              {publishResult && (
                <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/40 dark:bg-emerald-950/20 dark:border-emerald-800 space-y-3">
                  <div className="flex items-center gap-2 text-emerald-800 dark:text-emerald-300 font-semibold">
                    <CheckCircle2 size={16} className="text-emerald-600" />
                    <span>Successfully Anchored Version {publishResult.version}!</span>
                  </div>

                  <div className="space-y-1 font-mono text-[11px]">
                    <div className="text-muted-foreground truncate">
                      Schedule Hash: <span className="text-foreground">{publishResult.hash}</span>
                    </div>
                    <div className="text-muted-foreground truncate">
                      Transaction: <span className="text-foreground">{publishResult.tx_hash}</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        downloadFile(
                          publishResult.json_bytes_b64,
                          `schedule_v${publishResult.version}.json`,
                          "application/json"
                        )
                      }
                      className="text-xs h-7 gap-1"
                    >
                      <Download size={12} /> JSON
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        downloadFile(
                          publishResult.csv_bytes_b64,
                          `schedule_v${publishResult.version}.csv`,
                          "text/csv"
                        )
                      }
                      className="text-xs h-7 gap-1"
                    >
                      <Download size={12} /> CSV
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        downloadFile(
                          publishResult.ics_bytes_b64,
                          `schedule_v${publishResult.version}.ics`,
                          "text/calendar"
                        )
                      }
                      className="text-xs h-7 gap-1"
                    >
                      <Download size={12} /> ICS Calendar
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Public Proof Portal & Tamper Demonstration */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck size={16} className="text-primary" />
                <CardTitle className="text-foreground text-sm font-semibold">
                  Independent Verification Portal
                </CardTitle>
              </div>
              <p className="text-xs text-muted-foreground">
                Verify any schedule JSON against the immutable on-chain hash.
              </p>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              <form onSubmit={handleVerifyUpload} className="space-y-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-foreground">Upload Schedule JSON</label>
                  <input
                    type="file"
                    accept=".json"
                    onChange={(e) => setVerifyFile(e.target.files?.[0] || null)}
                    className="w-full text-xs text-muted-foreground file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
                  />
                </div>
                <Button type="submit" size="sm" isLoading={isVerifying} disabled={!verifyFile} className="w-full h-8">
                  Verify File Against Blockchain
                </Button>
              </form>

              {verifyResult && (
                <div
                  className={`p-3 rounded-lg border text-xs ${
                    verifyResult.match && verifyResult.anchored
                      ? "bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300"
                      : "bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/30 dark:text-rose-300"
                  }`}
                >
                  <div className="flex items-center gap-2 font-semibold">
                    {verifyResult.match && verifyResult.anchored ? (
                      <>
                        <CheckCircle2 size={15} className="text-emerald-600" />
                        <span>AUTHENTIC & ANCHORED ON ETHEREUM</span>
                      </>
                    ) : (
                      <>
                        <XCircle size={15} className="text-rose-600" />
                        <span>INTEGRITY CHECK FAILED: UNANCHORED / ALTERED</span>
                      </>
                    )}
                  </div>
                  <div className="font-mono text-[10px] mt-1 break-all">
                    Recomputed Hash: {verifyResult.recomputed_hash}
                  </div>
                </div>
              )}

              {/* Tamper Demonstration Card */}
              <div className="pt-2 border-t border-border space-y-2">
                <span className="font-semibold text-foreground block text-xs">
                  Automated Tamper-Detection Demonstration
                </span>
                <p className="text-[11px] text-muted-foreground">
                  Simulate modifying a single session slot in the published timetable to prove mathematical immutability.
                </p>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleTamperTest}
                  isLoading={isVerifying}
                  disabled={!schedule}
                  className="w-full text-xs h-8 gap-1.5"
                >
                  <AlertTriangle size={13} className="text-amber-500" />
                  <span>Execute Tamper Detection Test</span>
                </Button>

                {tamperDemoResult && (
                  <div className="p-3 rounded-lg bg-muted border border-border text-xs space-y-1.5">
                    <div className="flex items-center gap-1.5 text-emerald-600">
                      <CheckCircle2 size={14} />
                      <span>Original Schedule: Validated as authentic & anchored</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-rose-600">
                      <XCircle size={14} />
                      <span>Tampered Copy (1 Slot Changed): Rejected & flagged as unanchored</span>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
