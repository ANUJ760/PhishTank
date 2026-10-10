import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  CheckCheck,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  ArrowRight,
  AlertCircle,
  FileKey,
  CheckCircle2,
} from "lucide-react";

export function ApprovalsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Try to load any active options or conflict
  const [selectedUser, setSelectedUser] = useState<string>("Coordinator");
  const [approvalResults, setApprovalResults] = useState<Record<string, { ok: boolean; tx?: string; error?: string }>>({});
  const [appliedSuccess, setAppliedSuccess] = useState<string | null>(null);

  // We can query rules to see what options might be available
  const { data: conflictRes } = useQuery({
    queryKey: ["conflict-check"],
    queryFn: () => api.solve(true),
  });

  const { data: explanation } = useQuery({
    queryKey: ["active-explanation", conflictRes?.conflict?.rule_ids],
    queryFn: () => (conflictRes?.conflict ? api.conflicts.explain(conflictRes.conflict) : null),
    enabled: !!conflictRes?.conflict,
  });

  const approveMutation = useMutation({
    mutationFn: async ({ optionId, asUser }: { optionId: string; asUser: string }) => {
      const res = await api.conflicts.approve(optionId, asUser);
      setApprovalResults((prev) => ({
        ...prev,
        [optionId]: { ok: res.ok, tx: res.tx_hash, error: res.error },
      }));
      return res;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chain-events"] });
    },
  });

  const applyMutation = useMutation({
    mutationFn: async (optionId: string) => {
      const updated = await api.conflicts.apply(optionId);
      setAppliedSuccess(`Applied Option ${optionId}! Rule ${updated.id} parameters successfully updated.`);
      await api.solve(true);
      queryClient.invalidateQueries();
      return updated;
    },
  });

  const options = explanation?.options || [];
  const demoUsers = ["Coordinator", "Prof. Rao", "Dean", "Dept Head", "Prof. Mehta"];

  return (
    <div className="space-y-6 text-left">
      <div>
        <h2 className="text-xl font-bold tracking-tight text-foreground">On-Chain Multi-Party Approvals</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Two-step cryptographic consent pipeline: owner signs relaxation transaction &rarr; coordinator applies updated rule.
        </p>
      </div>

      <div className="p-3 rounded-lg border border-border bg-muted/30 text-xs text-muted-foreground space-y-1">
        <span className="font-semibold text-foreground flex items-center gap-1.5">
          <FileKey size={14} className="text-primary" />
          Anvil Local Consensus Note
        </span>
        <p>
          In this local environment, Anvil accounts serve as standing identities for institutional authorities. Smart contract access control strictly validates that the transaction signer matches the registered rule owner.
        </p>
      </div>

      {appliedSuccess && (
        <div className="p-4 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
            <span>{appliedSuccess}</span>
          </div>
          <Link to="/app/schedule">
            <Button size="sm" className="h-7 text-xs">
              View Updated Grid
            </Button>
          </Link>
        </div>
      )}

      {options.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-foreground">Pending Verified Relaxations ({options.length})</span>
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Sign as Demo Identity:</span>
              <select
                value={selectedUser}
                onChange={(e) => setSelectedUser(e.target.value)}
                className="h-8 rounded-md border border-border bg-background px-2 text-xs font-medium text-foreground focus:ring-1 focus:ring-primary"
              >
                {demoUsers.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {options.map((opt) => {
              const result = approvalResults[opt.id];
              const isOwner = selectedUser === opt.approver;

              return (
                <Card key={opt.id} className="p-5 space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-border pb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-foreground">{opt.id}</span>
                        <span className="text-xs text-muted-foreground">
                          Target Rule: <strong className="text-foreground">{opt.rule_id}</strong>
                        </span>
                      </div>
                      <p className="text-xs text-foreground font-medium mt-1">{opt.description}</p>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] text-muted-foreground block uppercase font-semibold">
                        Authorized Approver
                      </span>
                      <Badge variant="outline" className="font-semibold text-xs mt-0.5">
                        {opt.approver}
                      </Badge>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="p-2.5 rounded-lg bg-muted border border-border">
                      <span className="text-[10px] text-muted-foreground block">Proposed Parameters</span>
                      <pre className="font-mono text-[11px] mt-0.5 whitespace-pre-wrap">
                        {JSON.stringify(opt.new_params, null, 2)}
                      </pre>
                    </div>
                    <div className="p-2.5 rounded-lg bg-muted border border-border">
                      <span className="text-[10px] text-muted-foreground block">Cryptographic Digest</span>
                      <span className="font-mono text-[10px] text-muted-foreground break-all mt-0.5 block">
                        {opt.option_hash}
                      </span>
                    </div>
                  </div>

                  {/* On-Chain Result Box */}
                  {result && (
                    <div
                      className={`p-3 rounded-lg border text-xs ${
                        result.ok
                          ? "bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800"
                          : "bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/30 dark:text-rose-300 dark:border-rose-800"
                      }`}
                    >
                      {result.ok ? (
                        <div className="flex items-center justify-between">
                          <span className="flex items-center gap-1.5 font-medium">
                            <ShieldCheck size={14} className="text-emerald-600" />
                            Approved on-chain by {selectedUser}! Tx: {result.tx?.slice(0, 18)}...
                          </span>
                          <Button
                            size="sm"
                            onClick={() => applyMutation.mutate(opt.id)}
                            isLoading={applyMutation.isPending}
                            className="h-7 text-xs"
                          >
                            Step 2: Apply to Schedule
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5">
                          <ShieldAlert size={14} className="text-rose-600 shrink-0" />
                          <span>
                            <strong>On-Chain Revert:</strong> {result.error || "Not the rule owner."}
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Step 1 Approval Action Buttons */}
                  {!result?.ok && (
                    <div className="flex items-center justify-between pt-2">
                      <span className="text-[11px] text-muted-foreground">
                        Signing as: <strong className="text-foreground">{selectedUser}</strong>{" "}
                        {isOwner ? (
                          <span className="text-emerald-600 font-medium">(Authorized Owner)</span>
                        ) : (
                          <span className="text-rose-600 font-medium">(Will Revert on Chain)</span>
                        )}
                      </span>

                      <Button
                        size="sm"
                        onClick={() => approveMutation.mutate({ optionId: opt.id, asUser: selectedUser })}
                        isLoading={approveMutation.isPending}
                        variant={isOwner ? "default" : "outline"}
                        className="text-xs h-8 gap-1.5"
                      >
                        <UserCheck size={13} />
                        <span>Sign as {selectedUser}</span>
                      </Button>
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </div>
      ) : (
        <Card className="p-12 text-center text-xs text-muted-foreground space-y-3">
          <CheckCheck size={32} className="mx-auto text-muted-foreground/40 mb-2" />
          <h3 className="text-base font-semibold text-foreground">No Pending Approvals</h3>
          <p className="max-w-md mx-auto">
            When conflicts arise and verified options are synthesized in Conflict Studio, they will appear here for cryptographic owner sign-off.
          </p>
          <div className="pt-2">
            <Link to="/app/conflicts">
              <Button variant="outline" size="sm" className="text-xs">
                Go to Conflict Studio
              </Button>
            </Link>
          </div>
        </Card>
      )}
    </div>
  );
}
