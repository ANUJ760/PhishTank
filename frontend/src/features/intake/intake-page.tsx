import React, { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api-client";
import { Rule, IngestSheetResult } from "@/types/api";
import {
  FileText,
  Mic,
  Image as ImageIcon,
  FileSpreadsheet,
  ArrowRight,
} from "lucide-react";

export function IntakePage() {
  const [activeTab, setActiveTab] = useState<"text" | "audio" | "image" | "sheet">("text");

  // Inputs
  const [textInput, setTextInput] = useState("Prof. Rao cannot teach Monday morning between 09:00 and 12:00.");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // States
  const [isLoading, setIsLoading] = useState(false);
  const [extractedRules, setExtractedRules] = useState<Rule[]>([]);
  const [sheetMetrics, setSheetMetrics] = useState<IngestSheetResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const rules = await api.intake.text(textInput);
      setExtractedRules(rules);
      setSheetMetrics(null);
    } catch (err: any) {
      setError(err?.message || "Text intake failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    setIsLoading(true);
    setError(null);
    try {
      if (activeTab === "audio") {
        const rules = await api.intake.audio(selectedFile);
        setExtractedRules(rules);
        setSheetMetrics(null);
      } else if (activeTab === "image") {
        const rules = await api.intake.image(selectedFile);
        setExtractedRules(rules);
        setSheetMetrics(null);
      } else if (activeTab === "sheet") {
        const res = await api.intake.sheet(selectedFile);
        setExtractedRules(res.rules);
        setSheetMetrics(res);
      }
    } catch (err: any) {
      setError(err?.message || "File processing failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6 text-left pb-12">
      <div>
        <h2 className="text-xl font-bold tracking-tight text-white">Constraint & Rule Intake</h2>
        <p className="text-xs text-zinc-400 mt-0.5">
          Extract structured scheduling constraints from natural text, voice recordings, visual boards, or spreadsheets.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-white/5 gap-6 text-xs font-medium select-none">
        <button
          onClick={() => { setActiveTab("text"); setSelectedFile(null); setError(null); }}
          className={`flex items-center gap-1.5 pb-2.5 border-b-2 transition-colors ${
            activeTab === "text"
              ? "border-white text-white font-semibold"
              : "border-transparent text-zinc-400 hover:text-white"
          }`}
        >
          <FileText size={15} /> Natural Text
        </button>
        <button
          onClick={() => { setActiveTab("audio"); setSelectedFile(null); setError(null); }}
          className={`flex items-center gap-1.5 pb-2.5 border-b-2 transition-colors ${
            activeTab === "audio"
              ? "border-white text-white font-semibold"
              : "border-transparent text-zinc-400 hover:text-white"
          }`}
        >
          <Mic size={15} /> Audio Memo (WAV)
        </button>
        <button
          onClick={() => { setActiveTab("image"); setSelectedFile(null); setError(null); }}
          className={`flex items-center gap-1.5 pb-2.5 border-b-2 transition-colors ${
            activeTab === "image"
              ? "border-white text-white font-semibold"
              : "border-transparent text-zinc-400 hover:text-white"
          }`}
        >
          <ImageIcon size={15} /> Board Photo
        </button>
        <button
          onClick={() => { setActiveTab("sheet"); setSelectedFile(null); setError(null); }}
          className={`flex items-center gap-1.5 pb-2.5 border-b-2 transition-colors ${
            activeTab === "sheet"
              ? "border-white text-white font-semibold"
              : "border-transparent text-zinc-400 hover:text-white"
          }`}
        >
          <FileSpreadsheet size={15} /> Spreadsheet (XLSX)
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form Panel */}
        <div className="glass-box p-6 space-y-4">
          <div className="border-b border-white/5 pb-3">
            <h3 className="text-white text-sm font-semibold capitalize">
              {activeTab} Intake Sandbox
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Submit unprocessed constraints for LLM extraction and validation.
            </p>
          </div>

          {error && (
            <div className="p-3 rounded-xl border border-white/10 bg-white/[0.02] text-xs text-zinc-300">
              {error}
            </div>
          )}

          {activeTab === "text" ? (
            <form onSubmit={handleTextSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Faculty Constraint Prompt</label>
                <textarea
                  rows={4}
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  placeholder="Enter unstructured requirement..."
                  className="w-full p-3 rounded-xl bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20 resize-none"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="h-8 px-5 rounded-full bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all shadow-sm disabled:opacity-50"
              >
                {isLoading ? "Extracting..." : "Process Text with LLM"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleFileSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Select File</label>
                <input
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full p-2 rounded-xl bg-zinc-900 border border-white/10 text-xs text-zinc-300 file:mr-3 file:py-1 file:px-3 file:rounded-full file:border-0 file:bg-white file:text-zinc-950 file:text-xs file:font-medium"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={isLoading || !selectedFile}
                className="h-8 px-5 rounded-full bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all shadow-sm disabled:opacity-50"
              >
                {isLoading ? "Executing Sandbox..." : "Process File with Sandbox"}
              </button>
            </form>
          )}

          {sheetMetrics && (
            <div className="p-3.5 rounded-xl border border-white/5 bg-white/[0.02] text-xs space-y-1.5 mt-4">
              <span className="font-semibold text-white block">Docker Execution Metrics:</span>
              <div className="grid grid-cols-2 gap-2 text-zinc-400 text-[11px]">
                <div>Execution Time: <span className="text-zinc-200">{sheetMetrics.seconds}s</span></div>
                <div>Parser Attempts: <span className="text-zinc-200">{sheetMetrics.attempts}</span></div>
                <div>Cache Hit: <span className="text-zinc-200">{sheetMetrics.cache_hit ? "Yes" : "No"}</span></div>
                <div>Tokens Consumed: <span className="text-zinc-200">{sheetMetrics.tokens_used}</span></div>
              </div>
            </div>
          )}
        </div>

        {/* Results Panel */}
        <div className="glass-box p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <div>
              <h3 className="text-white text-sm font-semibold">Extracted Rules</h3>
              <p className="text-xs text-zinc-400 mt-0.5">Candidate draft rules awaiting human confirmation</p>
            </div>
            {extractedRules.length > 0 && (
              <Link to="/app/rules">
                <button className="h-7 px-3 rounded-full bg-zinc-900 border border-white/10 text-xs text-zinc-300 hover:text-white flex items-center gap-1">
                  <span>Review All</span>
                  <ArrowRight size={11} />
                </button>
              </Link>
            )}
          </div>

          <div className="space-y-3">
            {extractedRules.length === 0 ? (
              <div className="py-16 text-center text-xs text-zinc-500">
                No draft rules extracted in this session. Submit text or upload a document to begin.
              </div>
            ) : (
              extractedRules.map((rule) => (
                <div key={rule.id} className="p-3.5 rounded-xl border border-white/10 bg-[#16161c]/80 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-white">{rule.id}</span>
                    <span className="px-2.5 py-0.5 rounded-full bg-zinc-800 text-zinc-300 text-[10px]">
                      {rule.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-[11px] text-zinc-400">
                    Type: <span className="font-mono text-zinc-300">{rule.type}</span> &bull; Owner: {rule.owner}
                  </div>
                  {rule.evidence && (
                    <p className="text-[11px] text-zinc-400 italic bg-white/[0.02] p-2 rounded-lg border border-white/5">
                      &quot;{Array.isArray(rule.evidence) ? rule.evidence.map((e: any) => e.ref || e.kind || JSON.stringify(e)).join(", ") : String(rule.evidence)}&quot;
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
