import React, { useState, useRef, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api-client";
import { Rule, DataDumpResult, ExtractedRuleCard, Roster } from "@/types/api";
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
  Layers,
  Cpu,
  Calendar,
  Clock,
  UserX,
  Building,
  Pin,
  ShieldCheck,
  Search,
  Check,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Filter,
  Plus,
} from "lucide-react";
import { toast } from "sonner";

const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const SLOT_WINDOWS: Record<number, string> = {
  0: "09:00 - 10:00",
  1: "10:00 - 11:00",
  2: "11:00 - 12:00",
  3: "12:00 - 13:00",
  4: "14:00 - 15:00",
  5: "15:00 - 16:00",
};

function formatSlots(slots: number[] = []): string {
  if (!slots || slots.length === 0) return "Unspecified";
  const sorted = [...slots].sort((a, b) => a - b);
  if (sorted.length === 3 && sorted[0] === 0 && sorted[2] === 2) return "Morning (09:00 - 12:00)";
  if (sorted.length === 3 && sorted[0] === 3 && sorted[2] === 5) return "Afternoon (12:00 - 16:00)";
  if (sorted.length === 6) return "Full Day (09:00 - 16:00)";
  if (sorted.length === 1) return SLOT_WINDOWS[sorted[0]] || `Slot ${sorted[0]}`;
  const start = (SLOT_WINDOWS[sorted[0]] || `Slot ${sorted[0]}`).split(" - ")[0];
  const end = (SLOT_WINDOWS[sorted[sorted.length - 1]] || `Slot ${sorted[sorted.length - 1]}`).split(" - ")[1] || "";
  return `${start} - ${end} (Slots ${sorted.join(", ")})`;
}

export function IntakePage() {
  const [roster, setRoster] = useState<Roster | null>(null);

  // Inputs
  const [instructions, setInstructions] = useState(
    "Find faculty availability, room restrictions, and teaching requirements."
  );
  const [notes, setNotes] = useState("");
  const [files, setFiles] = useState<File[]>([]);

  // States
  const [isLoading, setIsLoading] = useState(false);
  const [dumpResult, setDumpResult] = useState<DataDumpResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Card UI states
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [confirmedRules, setConfirmedRules] = useState<Record<string, boolean>>({});
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({});

  useEffect(() => {
    api.roster().then((r) => {
      setRoster(r);
    }).catch(() => {});
  }, []);

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
    setDumpResult(null);
    setSearchQuery("");
    setFilterCategory("all");
    setConfirmedRules({});
    setExpandedDetails({});
    setError(null);
    try {
      const res = await api.intake.dump(files, instructions, notes);
      setDumpResult(res);
      toast.success(`Input processed. ${res.rules.length} draft rule${res.rules.length === 1 ? "" : "s"} extracted.`);
    } catch (err: any) {
      setError(err?.message || "Data dump intake failed");
      toast.error("Failed to process data dump");
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmRule = async (ruleId: string) => {
    setConfirmingId(ruleId);
    try {
      await api.rules.confirm(ruleId);
      setConfirmedRules((prev) => ({ ...prev, [ruleId]: true }));
      toast.success(`Rule ${ruleId} activated and applied to timetable solver.`);
    } catch (err: any) {
      toast.error(err?.message || `Failed to confirm rule ${ruleId}`);
    } finally {
      setConfirmingId(null);
    }
  };

  const toggleDetails = (ruleId: string) => {
    setExpandedDetails((prev) => ({ ...prev, [ruleId]: !prev[ruleId] }));
  };

  const loadPreset = (type: "college" | "relief" | "hospital") => {
    if (type === "college") {
      setInstructions("Extract faculty availability, room restrictions, and instructor qualification constraints for the semester timetable.");
      setNotes("");
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

  // Convert raw rules to rich cards if rule_cards not provided
  const ruleCards: ExtractedRuleCard[] = useMemo(() => {
    if (!dumpResult) return [];
    if (dumpResult.rule_cards && dumpResult.rule_cards.length > 0) {
      return dumpResult.rule_cards;
    }
    // Fallback generator from raw rules
    return dumpResult.rules.map((r) => {
      const p = r.params || {};
      const dayName = typeof p.day === "number" ? (DAY_NAMES[p.day] || `Day ${p.day}`) : "All Days";
      const timeWindow = p.slots ? formatSlots(p.slots) : "All Hours";
      let category = "Operational Constraint";
      let headline = `Constraint: ${r.type}`;
      let plainDesc = Object.entries(p).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" • ") || "Operational constraint.";
      let targetEntity = "Entity";

      if (r.type === "teacher_unavailable") {
        category = "Faculty Availability";
        targetEntity = p.teacher || "Faculty";
        headline = `${targetEntity} Unavailable on ${dayName}`;
        plainDesc = `${targetEntity} cannot be scheduled on ${dayName} during ${timeWindow}.`;
      } else if (r.type === "room_unavailable") {
        category = "Facility Maintenance";
        targetEntity = p.room || "Room";
        headline = `Facility Offline: ${targetEntity} (${dayName})`;
        plainDesc = `${targetEntity} is taken offline for maintenance on ${dayName} during ${timeWindow}.`;
      } else if (r.type === "pin_session") {
        category = "Session Lock";
        targetEntity = p.session_id || "Session";
        headline = `Locked Slot: ${targetEntity}`;
        plainDesc = `Locks ${targetEntity} to ${dayName} during ${timeWindow}.`;
      } else if (r.type === "only_qualified") {
        category = "Instructor Qualification";
        targetEntity = p.session_id || "Session";
        headline = `Qualification: ${targetEntity}`;
        plainDesc = `${targetEntity} must only be assigned to qualified instructor(s): ${(p.teachers || []).join(", ")}.`;
      }

      return {
        id: r.id,
        type: r.type,
        owner: r.owner,
        params: p,
        status: r.status,
        category,
        headline,
        plain_description: plainDesc,
        target_entity: targetEntity,
        day_name: dayName,
        time_window: timeWindow,
        slots_display: p.slots ? `Slots ${p.slots.join(", ")}` : "All Slots",
        timetable_impact: "Verified against live timetable parameters.",
        has_conflict: false,
        evidence_ref: r.evidence?.[0]?.ref || "data-dump",
      };
    });
  }, [dumpResult]);

  // Filtered cards
  const filteredCards = useMemo(() => {
    return ruleCards.filter((card) => {
      const matchesSearch =
        searchQuery === "" ||
        card.headline.toLowerCase().includes(searchQuery.toLowerCase()) ||
        card.plain_description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        card.target_entity.toLowerCase().includes(searchQuery.toLowerCase()) ||
        card.id.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCat =
        filterCategory === "all" ||
        (filterCategory === "faculty" && card.type === "teacher_unavailable") ||
        (filterCategory === "room" && card.type === "room_unavailable") ||
        (filterCategory === "lock" && card.type === "pin_session") ||
        (filterCategory === "qualification" && card.type === "only_qualified") ||
        (filterCategory === "conflicts" && card.has_conflict);

      return matchesSearch && matchesCat;
    });
  }, [ruleCards, searchQuery, filterCategory]);

  const conflictsCount = useMemo(() => ruleCards.filter((c) => c.has_conflict).length, [ruleCards]);

  return (
    <div className="space-y-6 text-left pb-16 max-w-6xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-zinc-100" />
            Timetable & constraints
          </h2>
          <p className="text-base text-zinc-400 mt-0.5">
            Upload your timetable and add any scheduling restrictions.
          </p>
        </div>

        {/* Quick Presets */}
        <details className="text-sm text-zinc-300">
          <summary className="cursor-pointer py-2">Try an example</summary>
          <div className="flex flex-wrap gap-2 mt-2">
          <button
            onClick={() => loadPreset("college")}
            type="button"
            className="min-h-10 px-2.5 rounded-md bg-zinc-900 border border-white/10 text-zinc-300 hover:text-white text-sm transition-colors"
          >
            Academic Timetable
          </button>
          <button
            onClick={() => loadPreset("relief")}
            type="button"
            className="min-h-10 px-2.5 rounded-md bg-zinc-900 border border-white/10 text-zinc-300 hover:text-white text-sm transition-colors"
          >
            Disaster Relief
          </button>
          <button
            onClick={() => loadPreset("hospital")}
            type="button"
            className="min-h-10 px-2.5 rounded-md bg-zinc-900 border border-white/10 text-zinc-300 hover:text-white text-sm transition-colors"
          >
            Hospital OR
          </button>
          </div>
        </details>
      </div>

      <form onSubmit={handleSubmitDump} className="space-y-6">
        {/* Step 1: Prompt & Instructions Box */}
        <div className="glass-box p-5 sm:p-6 space-y-3">
          <div className="flex items-center justify-between border-b border-white/5 pb-2.5">
            <label htmlFor="intake-instructions" className="text-base font-semibold text-white flex items-center gap-2">
              <Cpu size={14} className="text-zinc-300" />
              1. What should we check?
            </label>
          </div>
          <textarea
            id="intake-instructions"
            rows={2}
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="Describe what you want to check in your timetable."
            className="w-full p-3 rounded-lg bg-zinc-900/90 border border-white/10 text-base text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/25 transition-all resize-y leading-relaxed"
            required
          />
        </div>

        {/* Step 2: Unified Multi-File Data Dump Dropzone */}
        <div className="glass-box p-5 sm:p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-2.5">
            <label className="text-base font-semibold text-white flex items-center gap-2">
              <UploadCloud size={14} className="text-zinc-300" />
              2. Upload your timetable
            </label>
            <span className="text-sm text-zinc-400">
              {files.length} {files.length === 1 ? "file" : "files"} staged
            </span>
          </div>

          {/* Drag & Drop Zone */}
          <div
            role="button"
            tabIndex={0}
            aria-label="Choose timetable files"
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                fileInputRef.current?.click();
              }
            }}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-white/10 hover:border-white/20 bg-white/[0.01] hover:bg-white/[0.03] rounded-xl p-6 text-center cursor-pointer transition-all space-y-2"
          >
            <UploadCloud className="w-8 h-8 text-zinc-400 mx-auto" />
            <div className="space-y-1">
              <p className="text-base font-medium text-zinc-200">
                Drag and drop files here, or <span className="text-white underline">browse from your computer</span>
              </p>
              <p className="text-sm text-zinc-500">
                Upload a text-based PDF, Excel, or CSV timetable.
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
              <span className="text-sm font-medium text-zinc-400 block">Attached files</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                {files.map((file, idx) => (
                  <div
                    key={`${file.name}-${idx}`}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-900 border border-white/10 text-base"
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      {getFileIcon(file.name)}
                      <div className="truncate">
                        <p className="font-medium text-zinc-200 truncate text-sm">{file.name}</p>
                        <p className="text-sm text-zinc-500">{formatFileSize(file.size)}</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveFile(idx);
                      }}
                      aria-label={`Remove ${file.name}`}
                      className="p-2 text-zinc-400 hover:text-white rounded hover:bg-white/5 transition-colors"
                    >
                      <X size={18} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Step 3: Raw Notes & Text Dump */}
        <div className="glass-box p-5 sm:p-6 space-y-3">
          <div className="flex items-center justify-between border-b border-white/5 pb-2.5">
            <label htmlFor="intake-notes" className="text-base font-semibold text-white flex items-center gap-2">
              <FileText size={14} className="text-zinc-300" />
              3. Add your constraints
            </label>
          </div>
          <textarea
            id="intake-notes"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="For example: Prof. Sharma is unavailable on Monday morning."
            className="w-full p-3 rounded-lg bg-zinc-900/90 border border-white/10 text-base text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/25 transition-all resize-y leading-relaxed"
          />
        </div>

        {error && (
          <div className="p-3.5 rounded-lg border border-red-500/20 bg-red-950/20 text-base text-red-300 flex items-center gap-2">
            <AlertTriangle size={14} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Action */}
        <div className="flex items-center justify-end gap-4 pt-1">


          <button
            type="submit"
            disabled={isLoading}
            className="min-h-12 px-6 rounded-lg bg-white text-zinc-950 font-semibold text-base hover:bg-zinc-200 transition-all flex items-center gap-2 shadow-sm active:scale-[0.98] disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <RefreshCw size={14} className="animate-spin" />
                <span>Checking timetable…</span>
              </>
            ) : (
              <>
                <Sparkles size={14} />
                <span>Find constraints</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Results Section */}
      {dumpResult && (
        <div className="space-y-6 pt-6 border-t border-white/10 animate-fade-in">
          {/* Top Banner & Navigation */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <CheckCircle2 size={18} className="text-emerald-400" />
                Your constraints
              </h3>
              <p className="text-base text-zinc-400 mt-1">Review each rule before applying it.</p>
            </div>

            <div className="flex items-center gap-2">
              <Link to="/app/rules">
                <button className="min-h-10 px-3.5 rounded-md bg-white text-zinc-950 font-medium text-base hover:bg-zinc-200 transition-all flex items-center gap-1.5 shadow-sm">
                  <span>View all rules</span>
                  <ArrowRight size={12} />
                </button>
              </Link>
            </div>
          </div>

          {dumpResult.warnings.length > 0 && (
            <details className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-5 text-base text-amber-100">
              <summary className="cursor-pointer font-medium">
                Review {dumpResult.warnings.length} parsing or scheduling notes before applying rules
              </summary>
              <ul className="mt-3 list-disc pl-5 space-y-2 leading-relaxed">
                {dumpResult.warnings.map((warning, index) => <li key={index}>{warning}</li>)}
              </ul>
            </details>
          )}

          {(dumpResult.timetable_classes?.length ?? 0) > 0 && (
            <details className="glass-box p-5 sm:p-6">
              <summary className="cursor-pointer text-base font-semibold text-zinc-200">
                Uploaded timetable · {dumpResult.timetable_classes!.length} extracted classes
              </summary>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-zinc-400"><tr>
                    {['Day', 'Time', 'Course', 'Faculty', 'Room'].map(label => <th key={label} className="p-3 font-medium">{label}</th>)}
                  </tr></thead>
                  <tbody>
                    {dumpResult.timetable_classes!.map((item, index) => (
                      <tr key={index} className="border-t border-white/10 text-zinc-200">
                        <td className="p-3">{item.day}</td>
                        <td className="p-3 whitespace-nowrap">{item.start}–{item.end}</td>
                        <td className="p-3">{item.course_code}</td>
                        <td className="p-3">{item.teachers.join(', ') || 'Not identified'}</td>
                        <td className="p-3">{item.room || 'Not specified'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="glass-box p-3.5 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-zinc-200">
                <Layers size={15} />
              </div>
              <div>
                <p className="text-sm text-zinc-400 font-medium">Rules found</p>
                <p className="text-base font-bold text-white">{ruleCards.length}</p>
              </div>
            </div>

            <div className="glass-box p-3.5 flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg border flex items-center justify-center ${
                conflictsCount > 0 ? "bg-amber-500/10 border-amber-500/20 text-amber-300" : "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
              }`}>
                {conflictsCount > 0 ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />}
              </div>
              <div>
                <p className="text-sm text-zinc-400 font-medium">Conflicts</p>
                <p className="text-base font-bold text-white">{conflictsCount}</p>
              </div>
            </div>

            <div className="glass-box p-3.5 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-zinc-200">
                <Cpu size={15} />
              </div>
              <div>
                <p className="text-sm text-zinc-400 font-medium">People & places</p>
                <p className="text-base font-bold text-white">{dumpResult.entities.length}</p>
              </div>
            </div>

            <div className="glass-box p-3.5 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-zinc-200">
                <FileText size={15} />
              </div>
              <div>
                <p className="text-sm text-zinc-400 font-medium">Files checked</p>
                <p className="text-base font-bold text-white">{dumpResult.processed_files.length}</p>
              </div>
            </div>
          </div>

          {/* Executive Synthesis */}
          <details open={dumpResult.rules.length === 0} className="glass-box p-5 sm:p-6 space-y-3">
            <summary className="cursor-pointer text-base font-semibold text-zinc-200">Analysis summary</summary>
            <p className="text-base text-zinc-200 leading-relaxed">
              {dumpResult.summary}
            </p>
            {dumpResult.processing?.map((step, index) => (
              <p key={index} className="text-sm text-zinc-400">
                {step.stage}: {step.status} ({step.model})
              </p>
            ))}
          </details>

          {/* Section: Human-Readable Constraint Cards */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <h4 className="text-lg font-semibold text-white flex items-center gap-2">
                  <CheckCircle2 size={15} className="text-emerald-400" />
                  Extracted Constraints ({filteredCards.length} of {ruleCards.length})
                </h4>
              </div>

              {/* Filters & Search */}
              <div className="flex flex-wrap items-center gap-2">
                {/* Search */}
                <div className="relative">
                  <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-400" />
                  <input
                    type="text"
                    aria-label="Search constraints"
                    placeholder="Search professors or rooms"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="min-h-10 pl-7 pr-2.5 rounded-md bg-zinc-900 border border-white/10 text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
                  />
                </div>

                {/* Category Pills */}
                <div className="flex flex-wrap items-center gap-1 bg-zinc-900 p-0.5 rounded-md border border-white/10 text-sm">
                  <button
                    onClick={() => setFilterCategory("all")}
                    type="button"
                    className={`px-3 py-2 rounded ${filterCategory === "all" ? "bg-white text-zinc-950 font-semibold" : "text-zinc-400 hover:text-white"}`}
                  >
                    All
                  </button>
                  <button
                    onClick={() => setFilterCategory("faculty")}
                    type="button"
                    className={`px-3 py-2 rounded ${filterCategory === "faculty" ? "bg-white text-zinc-950 font-semibold" : "text-zinc-400 hover:text-white"}`}
                  >
                    Faculty
                  </button>
                  <button
                    onClick={() => setFilterCategory("room")}
                    type="button"
                    className={`px-3 py-2 rounded ${filterCategory === "room" ? "bg-white text-zinc-950 font-semibold" : "text-zinc-400 hover:text-white"}`}
                  >
                    Rooms
                  </button>
                  <button
                    onClick={() => setFilterCategory("conflicts")}
                    type="button"
                    className={`px-3 py-2 rounded ${filterCategory === "conflicts" ? "bg-amber-400 text-zinc-950 font-semibold" : "text-zinc-400 hover:text-white"}`}
                  >
                    Conflicts ({conflictsCount})
                  </button>
                </div>
              </div>
            </div>

            {/* Cards List */}
            {filteredCards.length === 0 ? (
              <div className="glass-box p-8 text-center space-y-2">
                <AlertCircle size={20} className="text-zinc-500 mx-auto" />
                <p className="text-base font-medium text-zinc-300">{ruleCards.length === 0 ? "No constraints found yet." : "No matching constraints."}</p>
                <p className="text-sm text-zinc-400">{ruleCards.length === 0 ? <>No draft rules were extracted. Review the analysis summary for the reason, then <a href="#intake-notes" className="underline text-zinc-200 hover:text-white">edit your constraint and try again</a>.</> : "Clear your search or choose another filter."}</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {filteredCards.map((card) => {
                  const isConfirmed = confirmedRules[card.id] || card.status === "confirmed";
                  const isDetailsOpen = expandedDetails[card.id] || false;

                  return (
                    <div
                      key={card.id}
                      className="glass-box p-5 sm:p-6 rounded-xl border border-white/10 hover:border-white/20 transition-all space-y-3.5 relative overflow-hidden"
                    >
                      {/* Card Header */}
                      <div className="flex items-center justify-between gap-2 border-b border-white/5 pb-2.5">
                        <div className="flex items-center gap-2">
                          {/* Type icon & category */}
                          <span className={`px-2 py-0.5 rounded-full text-sm font-semibold flex items-center gap-1.5 ${
                            card.type === "teacher_unavailable"
                              ? "bg-rose-500/10 text-rose-300 border border-rose-500/20"
                              : card.type === "room_unavailable"
                              ? "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                              : card.type === "pin_session"
                              ? "bg-sky-500/10 text-sky-300 border border-sky-500/20"
                              : "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                          }`}>
                            {card.type === "teacher_unavailable" && <UserX size={11} />}
                            {card.type === "room_unavailable" && <Building size={11} />}
                            {card.type === "pin_session" && <Pin size={11} />}
                            {card.type === "only_qualified" && <ShieldCheck size={11} />}
                            <span>{card.category}</span>
                          </span>

                        </div>

                        <div className="flex items-center gap-2">
                          <span className={`px-1.5 py-0.5 rounded text-sm font-semibold font-mono uppercase ${
                            isConfirmed ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : "bg-zinc-800 text-zinc-400"
                          }`}>
                            {isConfirmed ? "Active" : "Draft"}
                          </span>
                        </div>
                      </div>

                      {/* Headline & Plain-English Description */}
                      <div className="space-y-1">
                        <h5 className="text-lg font-semibold text-white leading-snug">
                          {card.target_entity}
                        </h5>
                        <p className="text-base text-zinc-300 leading-relaxed">
                          {card.plain_description}
                        </p>
                      </div>

                      {/* Visual Parameter Badges */}
                      <div className="flex flex-wrap items-center gap-1.5 text-sm">
                        <span className="px-2 py-1 rounded bg-zinc-900 border border-white/10 text-zinc-200 flex items-center gap-1 font-medium">
                          <Calendar size={11} className="text-zinc-400" />
                          <span>{card.day_name}</span>
                        </span>
                        <span className="px-2 py-1 rounded bg-zinc-900 border border-white/10 text-zinc-200 flex items-center gap-1 font-medium">
                          <Clock size={11} className="text-zinc-400" />
                          <span>{card.time_window}</span>
                        </span>

                      </div>

                      {/* Timetable Impact Alert */}
                      {card.has_conflict && (
                        <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-950/25 text-base text-amber-200 leading-relaxed flex items-start gap-2">
                          <AlertTriangle size={18} className="shrink-0 mt-0.5 text-amber-400" />
                          <span>{card.timetable_impact}</span>
                        </div>
                      )}

                      {/* Card Action Footer */}
                      <div className="flex items-center justify-between pt-1 border-t border-white/5">
                        <button
                          type="button"
                          aria-expanded={isDetailsOpen}
                          onClick={() => toggleDetails(card.id)}
                          className="min-h-10 text-sm text-zinc-300 hover:text-white flex items-center gap-1 transition-colors"
                        >
                          {isDetailsOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                          <span>{isDetailsOpen ? "Hide details" : "Details"}</span>
                        </button>

                        <button
                          type="button"
                          disabled={isConfirmed || confirmingId === card.id}
                          onClick={() => handleConfirmRule(card.id)}
                          className={`min-h-10 px-3 rounded-md text-sm font-semibold transition-all flex items-center gap-1.5 ${
                            isConfirmed
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 cursor-default"
                              : "bg-white text-zinc-950 hover:bg-zinc-200 active:scale-[0.98] shadow-sm"
                          }`}
                        >
                          {confirmingId === card.id ? (
                            <>
                              <RefreshCw size={11} className="animate-spin" />
                              <span>Activating...</span>
                            </>
                          ) : isConfirmed ? (
                            <>
                              <Check size={11} />
                              <span>Applied</span>
                            </>
                          ) : (
                            <>
                              <Plus size={11} />
                              <span>Apply rule</span>
                            </>
                          )}
                        </button>
                      </div>

                      {/* Expandable Structured Rule details */}
                      {isDetailsOpen && (
                        <div className="pt-3 border-t border-white/10 space-y-3 animate-fade-in">
                          <p className="text-base text-zinc-300 leading-relaxed">{card.timetable_impact}</p>
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                              Rule details
                            </span>
                            <span className="text-sm font-mono text-zinc-500">
                              Ref: {card.evidence_ref || "Direct memo"}
                            </span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-base">
                            <div className="p-2 rounded-lg bg-zinc-900 border border-white/5">
                              <span className="text-zinc-500 block text-sm">Applies to</span>
                              <span className="font-semibold text-zinc-200 break-words block">{card.target_entity}</span>
                            </div>
                            <div className="p-2 rounded-lg bg-zinc-900 border border-white/5">
                              <span className="text-zinc-500 block text-sm">Schedule Day</span>
                              <span className="font-semibold text-zinc-200 break-words block">{card.day_name}</span>
                            </div>
                            <div className="p-2 rounded-lg bg-zinc-900 border border-white/5">
                              <span className="text-zinc-500 block text-sm">Time Window</span>
                              <span className="font-semibold text-zinc-200 break-words block">{card.time_window}</span>
                            </div>
                            <div className="p-2 rounded-lg bg-zinc-900 border border-white/5">
                              <span className="text-zinc-500 block text-sm">Owner</span>
                              <span className="font-semibold text-zinc-200 break-words block">{card.owner}</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <details className="glass-box p-5 sm:p-6">
            <summary className="cursor-pointer text-base font-semibold text-zinc-200">
              People, files & analysis notes ({dumpResult.warnings.length} warnings)
            </summary>
            <div className="mt-5 space-y-5">
          {/* Section: Identified Entities & Operational Insights */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
            {/* Cataloged Domain Entities */}
            <div className="glass-box p-5 sm:p-6 space-y-3">
              <div className="border-b border-white/5 pb-2.5 flex items-center justify-between">
                <h4 className="text-base font-semibold text-white flex items-center gap-2">
                  <Layers size={13} className="text-zinc-300" />
                  People, rooms & classes ({dumpResult.entities.length})
                </h4>
              </div>

              {dumpResult.entities.length === 0 ? (
                <p className="text-base text-zinc-500 py-4 text-center">No distinct entities cataloged.</p>
              ) : (
                <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                  {dumpResult.entities.map((ent, idx) => (
                    <div
                      key={`${ent.name}-${idx}`}
                      className="p-2.5 rounded-lg bg-zinc-900 border border-white/10 text-base flex items-center justify-between gap-3"
                    >
                      <div className="truncate">
                        <span className="font-semibold text-white text-base">{ent.name}</span>
                        {ent.details && (
                          <p className="text-sm text-zinc-400 truncate mt-0.5">{ent.details}</p>
                        )}
                      </div>
                      <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 text-sm font-mono shrink-0">
                        {ent.kind}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Operational Insights & Findings */}
            <div className="glass-box p-5 sm:p-6 space-y-3">
              <div className="border-b border-white/5 pb-2.5">
                <h4 className="text-base font-semibold text-white flex items-center gap-2">
                  <Lightbulb size={13} className="text-amber-400" />
                  Notes & warnings
                </h4>
              </div>

              {dumpResult.insights.length === 0 && dumpResult.warnings.length === 0 ? (
                <p className="text-base text-zinc-500 py-4 text-center">No operational patterns flagged.</p>
              ) : (
                <ul className="space-y-2 text-base text-zinc-300 max-h-72 overflow-y-auto pr-1">
                  {dumpResult.insights.map((ins, i) => (
                    <li key={`ins-${i}`} className="p-2 rounded bg-zinc-900/60 border border-white/5 flex items-start gap-2">
                      <CheckCircle2 size={13} className="shrink-0 mt-0.5 text-emerald-400" />
                      <span>{ins}</span>
                    </li>
                  ))}
                  {dumpResult.warnings.map((warn, i) => (
                    <li key={`warn-${i}`} className="p-2 rounded bg-amber-950/20 border border-amber-500/20 text-amber-200 flex items-start gap-2">
                      <AlertTriangle size={13} className="shrink-0 mt-0.5 text-amber-400" />
                      <span>{warn}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Section: Processed Files Breakdown */}
          {dumpResult.processed_files.length > 0 && (
            <div className="glass-box p-5 sm:p-6 space-y-3">
              <div className="border-b border-white/5 pb-2.5 flex items-center justify-between">
                <span className="text-sm font-semibold text-zinc-400 uppercase tracking-wider block">
                  Uploaded files ({dumpResult.processed_files.length})
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {dumpResult.processed_files.map((pf, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-zinc-900/80 border border-white/10 text-base space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 truncate">
                        {getFileIcon(pf.filename)}
                        <span className="font-semibold text-zinc-200 truncate">{pf.filename}</span>
                      </div>
                      <span className="text-sm uppercase font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                        {pf.file_type}
                      </span>
                    </div>
                    <p className="text-sm text-zinc-500">{formatFileSize(pf.size_bytes)}</p>
                    {pf.preview && (
                      <p className="text-sm text-zinc-400 font-mono bg-black/40 p-2 rounded truncate leading-relaxed">
                        {pf.preview}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
