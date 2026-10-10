import React, { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api-client";
import { Rule, IngestSheetResult } from "@/types/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  Mic,
  Image as ImageIcon,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  ShieldAlert,
  Cpu,
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
    <div className="space-y-6 text-left">
      <div>
        <h2 className="text-xl font-bold tracking-tight text-foreground">Constraint & Rule Intake</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Extract structured scheduling constraints from natural text, voice recordings, visual boards, or spreadsheets.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border gap-6 text-xs font-medium select-none">
        <button
          onClick={() => { setActiveTab("text"); setSelectedFile(null); setError(null); }}
          className={`flex items-center gap-1.5 pb-2.5 border-b-2 transition-colors ${
            activeTab === "text"
              ? "border-primary text-foreground font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileText size={15} /> Natural Text
        </button>
        <button
          onClick={() => { setActiveTab("audio"); setSelectedFile(null); setError(null); }}
          className={`flex items-center gap-1.5 pb-2.5 border-b-2 transition-colors ${
            activeTab === "audio"
              ? "border-primary text-foreground font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Mic size={15} /> Voice Note (WAV)
        </button>
        <button
          onClick={() => { setActiveTab("image"); setSelectedFile(null); setError(null); }}
          className={`flex items-center gap-1.5 pb-2.5 border-b-2 transition-colors ${
            activeTab === "image"
              ? "border-primary text-foreground font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <ImageIcon size={15} /> Board Photo (Image)
        </button>
        <button
          onClick={() => { setActiveTab("sheet"); setSelectedFile(null); setError(null); }}
          className={`flex items-center gap-1.5 pb-2.5 border-b-2 transition-colors ${
            activeTab === "sheet"
              ? "border-primary text-foreground font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileSpreadsheet size={15} /> Workload Spreadsheet
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive flex items-center gap-2">
          <AlertCircle size={15} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Input Forms */}
      <Card>
        <CardContent className="pt-6">
          {activeTab === "text" && (
            <form onSubmit={handleTextSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">Constraint Statement</label>
                <textarea
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-border bg-background p-3 text-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  placeholder="e.g. Prof. Rao is unavailable on Monday morning slots."
                  required
                />
              </div>
              <Button type="submit" isLoading={isLoading} size="sm">
                Extract Draft Rule
              </Button>
            </form>
          )}

          {activeTab !== "text" && (
            <form onSubmit={handleFileSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">
                  {activeTab === "audio" && "Select WAV Audio File"}
                  {activeTab === "image" && "Select Photo / Screenshot"}
                  {activeTab === "sheet" && "Select Excel Spreadsheet (.xlsx)"}
                </label>
                <Input
                  type="file"
                  accept={
                    activeTab === "audio"
                      ? "audio/wav,audio/*"
                      : activeTab === "image"
                      ? "image/png,image/jpeg"
                      : ".xlsx,.xls"
                  }
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  required
                />
                <p className="text-[11px] text-muted-foreground">
                  {activeTab === "sheet" && "Spreadsheets are parsed via a synthesized program in an isolated Docker sandbox container."}
                  {activeTab === "audio" && "Audio clips are processed through multimodal Gemma or fixture intake fallback."}
                </p>
              </div>
              <Button type="submit" isLoading={isLoading} disabled={!selectedFile} size="sm">
                Process File
              </Button>
            </form>
          )}
        </CardContent>
      </Card>

      {/* Sheet Sandbox Metrics Banner */}
      {sheetMetrics && (
        <Card className="bg-muted/30 border-primary/20">
          <CardContent className="pt-5 pb-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Cpu size={14} className="text-primary" />
                Docker Sandbox Parser Execution Metrics
              </span>
              <Badge variant={sheetMetrics.cache_hit ? "success" : "secondary"}>
                {sheetMetrics.cache_hit ? "Cache Hit" : "Synthesized & Cached"}
              </Badge>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-2.5 rounded-lg bg-card border border-border">
                <span className="text-[10px] text-muted-foreground block">Rules Extracted</span>
                <span className="text-sm font-bold text-foreground">{sheetMetrics.rules.length}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-card border border-border">
                <span className="text-[10px] text-muted-foreground block">Execution Time</span>
                <span className="text-sm font-bold text-foreground">{sheetMetrics.seconds.toFixed(2)}s</span>
              </div>
              <div className="p-2.5 rounded-lg bg-card border border-border">
                <span className="text-[10px] text-muted-foreground block">LLM Tokens Used</span>
                <span className="text-sm font-bold text-foreground">{sheetMetrics.tokens_used}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-card border border-border">
                <span className="text-[10px] text-muted-foreground block">Synthesis Attempts</span>
                <span className="text-sm font-bold text-foreground">{sheetMetrics.attempts || 1}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Extracted Draft Rules Display */}
      {extractedRules.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">
              Extracted Draft Rules ({extractedRules.length})
            </h3>
            <Link to="/app/rules">
              <Button variant="outline" size="sm" className="text-xs h-7 gap-1">
                Open Review Ledger <ArrowRight size={12} />
              </Button>
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {extractedRules.map((rule) => (
              <Card key={rule.id} className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-xs text-foreground">{rule.id}</span>
                    <Badge variant="secondary" className="capitalize text-[10px]">
                      {rule.type.replace("_", " ")}
                    </Badge>
                  </div>
                  <Badge variant="warning">{rule.status}</Badge>
                </div>

                <div className="text-xs text-muted-foreground space-y-1">
                  <div>
                    <span className="font-medium text-foreground">Owner:</span> {rule.owner}
                  </div>
                  <div className="font-mono text-[11px] bg-muted/50 p-1.5 rounded border border-border truncate">
                    {JSON.stringify(rule.params)}
                  </div>
                  {rule.evidence && rule.evidence.length > 0 && (
                    <div className="text-[10px] text-muted-foreground pt-1">
                      Evidence: {rule.evidence.map((e) => `${e.kind} (${e.ref})`).join(", ")}
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
