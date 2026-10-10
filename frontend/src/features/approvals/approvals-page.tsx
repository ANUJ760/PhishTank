import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import {
  CheckCheck,
  UserCheck,
  ArrowRight,
  FileKey,
} from "lucide-react";

export function ApprovalsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [selectedUser, setSelectedUser] = useState<string>("Coordinator");
  const [approvalResults, setApprovalResults] = useState<Record<string, { ok: boolean; tx?: string; error?: string }>>({});
  const [appliedSuccess, setAppliedSuccess] = useState<string | null>(null);

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
    <div className="space-y-6 text-left pb-12">
      <div>
        <h2 className="text-xl font-bold tracking-tight text-white">On-Chain Multi-Party Approvals</h2>
        <p className="text-xs text-zinc-400 mt-0.5">
          Two-step cryptographic consent pipeline: owner signs relaxation transaction &rarr; coordinator applies updated rule.
        </p>
      </div>

      <div className="p-3.5 rounded-2xl border border-white/10 bg-zinc-900/80 backdrop-blur-xl text-xs text-zinc-400 space-y-1">
        <span className="font-semibold text-white flex items-center gap-1.5">
          <FileKey size={14} className="text-zinc-300" />
          Anvil Local Consensus Note
        </span>
        <p>
          In this local environment, Anvil accounts serve as standing identities for institutional authorities. Smart contract access control strictly validates that the transaction signer matches the registered rule owner.
        </p>
      </div>

      {appliedSuccess && (
        <div className="p-4 rounded-2xl border border-white/10 bg-zinc-900/80 text-xs flex items-center justify-between text-zinc-200">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-zinc-300" />
            <span>{appliedSuccess}</span>
          </div>
          <Link to="/app/schedule">
            <button className="h-7 px-3 rounded-full bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all">
              View Updated Grid
            </button>
          </Link>
        </div>
      )}

      {options.length > 0 ? (
        <div className="space-y-6">
          {/* Identity switcher */}
          <div className="glass-box p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-0.5">
              <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                <UserCheck size={14} className="text-zinc-300" />
                Active On-Chain Signer Identity:
              </span>
              <p className="text-[11px] text-zinc-400">
                Switch accounts to demonstrate non-owner revert vs owner success.
              </p>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {demoUsers.map((u) => (
                <button
                  key={u}
                  onClick={() => setSelectedUser(u)}
                  className={`px-3 py-1 rounded-full text-xs transition-all ${
                    selectedUser === u
                      ? "bg-white text-zinc-950 font-medium shadow-xs"
                      : "bg-zinc-900 border border-white/5 text-zinc-400 hover:text-white"
                  }`}
                >
                  {u}
                </button>
              ))}
            </div>
          </div>

          {/* Relaxation approval cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {options.map((opt) => {
              const res = approvalResults[opt.id];
              const isOwner = selectedUser === opt.approver;

              return (
                <div key={opt.id} className="glass-box p-6 space-y-4">
                  <div className="flex items-start justify-between gap-2 border-b border-white/5 pb-3">
                    <div>
                      <h3 className="font-semibold text-white text-sm">Relax {opt.rule_id}</h3>
                      <p className="text-xs text-zinc-400 mt-0.5">Required Signer: <strong className="text-white font-mono">{opt.approver}</strong></p>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full bg-zinc-800 text-zinc-300 text-[10px] font-mono">
                      {opt.id}
                    </span>
                  </div>

                  <p className="text-xs text-zinc-300 leading-relaxed bg-white/[0.02] p-3 rounded-xl border border-white/5">
                    {opt.description}
                  </p>

                  {/* Step 1 & 2 actions */}
                  <div className="space-y-3 pt-2">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => approveMutation.mutate({ optionId: opt.id, asUser: selectedUser })}
                        disabled={approveMutation.isPending}
                        className="flex-1 h-8 rounded-full bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all flex items-center justify-center gap-1.5 shadow-sm active:scale-[0.98] disabled:opacity-50"
                      >
                        <CheckCheck size={13} />
                        <span>Sign as &quot;{selectedUser}&quot;</span>
                      </button>

                      {res?.ok && (
                        <button
                          onClick={() => applyMutation.mutate(opt.id)}
                          disabled={applyMutation.isPending}
                          className="h-8 px-4 rounded-full bg-zinc-900 border border-white/10 text-white font-medium text-xs hover:bg-zinc-800 transition-all flex items-center gap-1"
                        >
                          <span>Apply</span>
                          <ArrowRight size={12} />
                        </button>
                      )}
                    </div>

                    {res && (
                      <div className="p-3 rounded-xl border border-white/10 bg-white/[0.02] text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white">
                            {res.ok ? "On-Chain Approval Verified" : "Transaction Reverted"}
                          </span>
                        </div>
                        {res.tx && (
                          <div className="font-mono text-[10px] text-zinc-400 truncate">
                            Tx: {res.tx}
                          </div>
                        )}
                        {res.error && (
                          <p className="text-[11px] text-zinc-400">{res.error}</p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="glass-box p-12 text-center space-y-3">
          <h3 className="text-base font-semibold text-white">No Pending Relaxation Proposals</h3>
          <p className="text-xs text-zinc-400 max-w-md mx-auto">
            To view and test on-chain consent workflows, visit Conflict Studio and generate a conflict explanation.
          </p>
          <div className="pt-2">
            <Link to="/app/conflicts">
              <button className="h-8 px-4 rounded-full bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all">
                Go to Conflict Studio
              </button>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
