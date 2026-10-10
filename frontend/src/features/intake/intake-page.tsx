import React, { useState, useRef } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api-client";
import { Rule, DataDumpResult } from "@/types/api";
import {
  UploadCloud,
  FileSpreadsheet,
  FileText,
  Mic,
  Image as ImageIcon,
  FileCode,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  X,
  ArrowRight,
  RefreshCw,
  Plus,
  Layers,
  Cpu,
} from "lucide-react";
import { toast } from "sonner";

export function IntakePage() {
  // Inputs
  const [instructions, setInstructions] = useState(
    "Extract all faculty availability constraints, room requirements, and qualification rules. Flag any overlapping time preferences."
  );
  const [notes, setNotes] = useState(
    "Email from Dept Head: Prof. Rao has a committee meeting Monday morning from 09:00 to 12:00. DB_LAB sessions require qualified faculty only."
  );
  const [files, setFiles] = useState<File[]>([]);

  // States
  const [isLoading, setIsLoading] = useState(false);
  const [dumpResult, setDumpResult] = useState<DataDumpResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      setFiles((prev) => [...prev, ...droppedFiles]);
    }
  };

  const handleSubmitDump = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0 && !notes.trim()) {
      setError("Please attach at least one file or enter data notes in the dump area.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.intake.dump(files, instructions, notes);
      setDumpResult(res);
      toast.success(`Data dump processed! ${res.rules.length} constraints extracted by Gemma.`);
    } catch (err: any) {
      setError(err?.message || "Data dump intake failed");
      toast.error("Failed to process data dump");
    } finally {
      setIsLoading(false);
    }
  };

  const loadPreset = (type: "college" | "relief" | "hospital") => {
    if (type === "college") {
      setInstructions("Extract faculty availability, room restrictions, and instructor qualification constraints for the upcoming semester timetable.");
      setNotes("Memo from Dean: Prof. Rao cannot teach Monday morning (slots 0 and 1). DB_LAB session must only be assigned to qualified faculty [Prof. Rao].");
    } else if (type === "relief") {
      setInstructions("Consolidate disaster relief supply requests across all flood camps. Prioritize drinking water and medical kits, and respect vehicle payload caps.");
      setNotes("Field Dispatch: Camp Delta (pop 850) has severe drinking water shortage, request 600 units. Camp Alpha cut off by road, requires helicopter transport only.");
    } else {
      setInstructions("Extract emergency surgical cases, prioritize Level 1 trauma resuscitation, and schedule required surgeon specialties in Operating Theatres.");
      setNotes("ER Shift Log: Patient C-101 requires immediate vascular surgery (60 min). OR-1 and OR-2 are fully sterile and available with anesthesia teams.");
    }
    setError(null);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    if (["xlsx", "xls", "csv"].includes(ext || "")) return <FileSpreadsheet size={14} className="text-emerald-400" />;
    if (["wav", "mp3", "ogg", "m4a"].includes(ext || "")) return <Mic size={14} className="text-amber-400" />;
    if (["png", "jpg", "jpeg", "webp"].includes(ext || "")) return <ImageIcon size={14} className="text-blue-400" />;
    if (["json", "xml", "csv"].includes(ext || "")) return <FileCode size={14} className="text-purple-400" />;
    return <FileText size={14} className="text-zinc-400" />;
  };

  return (
    <div className="space-y-6 text-left pb-12 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-white" />
            Universal Multi-Modal Data Dump Studio
          </h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            Dump spreadsheets, audio memos, board photos, and raw notes together. Gemma synthesizes all inputs according to your exact instructions.
          </p>
        </div>

        {/* Quick Presets */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-zinc-500 font-medium hidden md:inline">Presets:</span>
          <button
            onClick={() => loadPreset("college")}
            type="button"
            className="h-7 px-2.5 rounded-md bg-zinc-900 border border-white/10 text-zinc-300 hover:text-white text-[11px] transition-colors"
          >
            Academic Timetable
          </button>
          <button
            onClick={() => loadPreset("relief")}
            type="button"
            className="h-7 px-2.5 rounded-md bg-zinc-900 border border-white/10 text-zinc-300 hover:text-white text-[11px] transition-colors"
          >
            Disaster Relief
          </button>
          <button
            onClick={() => loadPreset("hospital")}
            type="button"
            className="h-7 px-2.5 rounded-md bg-zinc-900 border border-white/10 text-zinc-300 hover:text-white text-[11px] transition-colors"
          >
            Hospital OR
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmitDump} className="space-y-6">
        {/* Step 1: Prompt & Instructions Box */}
        <div className="glass-box p-5 space-y-3">
          <div className="flex items-center justify-between border-b border-white/5 pb-2.5">
            <label className="text-xs font-semibold text-white flex items-center gap-2">
              <Cpu size={14} className="text-zinc-300" />
              1. What is required out of this data dump? (Gemma Instructions)
            </label>
            <span className="text-[10px] text-zinc-400 font-mono">Gemma 4B / 12B Reasoning</span>
          </div>
          <textarea
            rows={3}
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="Type your instructions here: What specific rules, constraints, allocations, or insights do you want Gemma to extract and prioritize from the dumped files?"
            className="w-full p-3 rounded-lg bg-zinc-900/90 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/25 transition-all resize-none leading-relaxed"
            required
          />
        </div>

        {/* Step 2: Unified Multi-File Data Dump Dropzone */}
        <div className="glass-box p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-2.5">
            <label className="text-xs font-semibold text-white flex items-center gap-2">
              <UploadCloud size={14} className="text-zinc-300" />
              2. Data Dump Files (Spreadsheets, Photos, Voice Recordings, Documents)
            </label>
            <span className="text-[10px] text-zinc-400">
              {files.length} {files.length === 1 ? "file" : "files"} staged
            </span>
          </div>

          {/* Drag & Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-white/10 hover:border-white/20 bg-white/[0.01] hover:bg-white/[0.03] rounded-xl p-6 text-center cursor-pointer transition-all space-y-2"
          >
            <UploadCloud className="w-8 h-8 text-zinc-400 mx-auto" />
            <div className="space-y-1">
              <p className="text-xs font-medium text-zinc-200">
                Drag and drop files here, or <span className="text-white underline">browse from your computer</span>
              </p>
              <p className="text-[11px] text-zinc-500">
                Supports all formats simultaneously: XLSX, CSV, PNG, JPG, WAV, MP3, PDF, TXT, JSON
              </p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFilesSelected}
              className="hidden"
            />
          </div>

          {/* Staged File List */}
          {files.length > 0 && (
            <div className="space-y-2 pt-2">
              <span className="text-[11px] font-medium text-zinc-400 block">Staged Files in Data Dump:</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                {files.map((file, idx) => (
                  <div
                    key={`${file.name}-${idx}`}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-900 border border-white/10 text-xs"
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      {getFileIcon(file.name)}
                      <div className="truncate">
                        <p className="font-medium text-zinc-200 truncate text-[11px]">{file.name}</p>
                        <p className="text-[10px] text-zinc-500">{formatFileSize(file.size)}</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveFile(idx);
                      }}
                      className="p-1 text-zinc-500 hover:text-white rounded hover:bg-white/5 transition-colors"
                    >
                      <X size={13} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Step 3: Raw Notes & Text Dump */}
        <div className="glass-box p-5 space-y-3">
          <div className="flex items-center justify-between border-b border-white/5 pb-2.5">
            <label className="text-xs font-semibold text-white flex items-center gap-2">
              <FileText size={14} className="text-zinc-300" />
              3. Raw Notes / Direct Paste Dump (Optional)
            </label>
            <span className="text-[10px] text-zinc-500">Paste logs, dispatch reports, memos, or verbal transcriptions</span>
          </div>
          <textarea
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Paste any unstructured raw text, memos, or email threads here to be processed alongside the files..."
            className="w-full p-3 rounded-lg bg-zinc-900/90 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/25 transition-all resize-none leading-relaxed font-mono text-[11px]"
          />
        </div>

        {error && (
          <div className="p-3.5 rounded-lg border border-red-500/20 bg-red-950/20 text-xs text-red-300 flex items-center gap-2">
            <AlertTriangle size={14} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Action */}
        <div className="flex items-center justify-between gap-4 pt-1">
          <div className="text-[11px] text-zinc-500 flex items-center gap-2">
            <Layers size={13} />
            <span>Consolidated processing via Gemma Multi-Modal Pipeline</span>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="h-9 px-6 rounded-lg bg-white text-zinc-950 font-semibold text-xs hover:bg-zinc-200 transition-all flex items-center gap-2 shadow-sm active:scale-[0.98] disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <RefreshCw size={14} className="animate-spin" />
                <span>Gemma is Synthesizing Data Dump...</span>
              </>
            ) : (
              <>
                <Sparkles size={14} />
                <span>Process Data Dump with Gemma</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Results Section */}
      {dumpResult && (
        <div className="space-y-6 pt-4 border-t border-white/10">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-400" />
                Gemma Data Dump Analysis & Extractions
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                Executed instructions: &quot;{dumpResult.instructions_executed}&quot;
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Link to="/app/rules">
                <button className="h-8 px-3.5 rounded-md bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all flex items-center gap-1.5 shadow-sm">
                  <span>Review Constraints in Studio</span>
                  <ArrowRight size={12} />
                </button>
              </Link>
            </div>
          </div>

          {/* Executive Synthesis */}
          <div className="glass-box p-5 space-y-2 border-l-2 border-l-white">
            <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider block">
              Gemma Executive Synthesis
            </span>
            <p className="text-xs text-zinc-200 leading-relaxed">
              {dumpResult.summary}
            </p>
          </div>

          {/* Grid: Extracted Constraints & Domain Entities */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Extracted Constraints */}
            <div className="glass-box p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-white/5 pb-2.5">
                <h4 className="text-xs font-semibold text-white flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-emerald-400" />
                  Extracted Rules & Constraints ({dumpResult.rules.length})
                </h4>
                <span className="text-[10px] text-zinc-400 font-mono">Draft Status</span>
              </div>

              {dumpResult.rules.length === 0 ? (
                <p className="text-xs text-zinc-500 py-6 text-center">No explicit constraint rules found.</p>
              ) : (
                <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                  {dumpResult.rules.map((rule) => (
                    <div
                      key={rule.id}
                      className="p-3 rounded-lg bg-zinc-900 border border-white/10 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-white text-[11px]">{rule.id}</span>
                        <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 text-[10px] font-mono">
                          {rule.type}
                        </span>
                      </div>
                      <div className="text-[11px] text-zinc-400">
                        Owner: <strong className="text-zinc-200">{rule.owner}</strong>
                      </div>
                      <pre className="p-2 rounded bg-black/60 border border-white/5 font-mono text-[10px] text-zinc-300 overflow-x-auto">
                        {JSON.stringify(rule.params, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Identified Entities & Insights */}
            <div className="space-y-6">
              {/* Identified Entities */}
              <div className="glass-box p-5 space-y-3">
                <div className="border-b border-white/5 pb-2.5">
                  <h4 className="text-xs font-semibold text-white flex items-center gap-2">
                    <Layers size={13} className="text-zinc-300" />
                    Identified Domain Entities ({dumpResult.entities.length})
                  </h4>
                </div>

                {dumpResult.entities.length === 0 ? (
                  <p className="text-xs text-zinc-500 py-4 text-center">No distinct entities cataloged.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {dumpResult.entities.map((ent, idx) => (
                      <div
                        key={`${ent.name}-${idx}`}
                        className="px-2.5 py-1 rounded-md bg-zinc-900 border border-white/10 text-xs flex items-center gap-1.5"
                      >
                        <span className="font-medium text-white">{ent.name}</span>
                        <span className="text-[10px] text-zinc-500 font-mono">({ent.kind})</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Insights & Discrepancy Warnings */}
              {(dumpResult.insights.length > 0 || dumpResult.warnings.length > 0) && (
                <div className="glass-box p-5 space-y-3">
                  <div className="border-b border-white/5 pb-2.5">
                    <h4 className="text-xs font-semibold text-white flex items-center gap-2">
                      <Lightbulb size={13} className="text-amber-400" />
                      Gemma Operational Insights & Findings
                    </h4>
                  </div>

                  <ul className="space-y-1.5 text-xs text-zinc-300">
                    {dumpResult.insights.map((ins, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-zinc-500">&bull;</span>
                        <span>{ins}</span>
                      </li>
                    ))}
                    {dumpResult.warnings.map((warn, i) => (
                      <li key={`w-${i}`} className="flex items-start gap-2 text-amber-300">
                        <AlertTriangle size={13} className="shrink-0 mt-0.5 text-amber-400" />
                        <span>{warn}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Processed Files Breakdown */}
          {dumpResult.processed_files.length > 0 && (
            <div className="glass-box p-5 space-y-3">
              <span className="text-[11px] font-semibold text-zinc-400 block uppercase tracking-wider">
                Processed Dump Files Breakdown
              </span>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {dumpResult.processed_files.map((pf, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-zinc-900/80 border border-white/10 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-zinc-200 truncate">{pf.filename}</span>
                      <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                        {pf.file_type}
                      </span>
                    </div>
                    <p className="text-[10px] text-zinc-500">{formatFileSize(pf.size_bytes)}</p>
                    {pf.preview && (
                      <p className="text-[10px] text-zinc-400 font-mono bg-black/40 p-2 rounded truncate">
                        {pf.preview}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
