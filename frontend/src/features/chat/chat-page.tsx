import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Bot,
  User as UserIcon,
  Sparkles,
  RotateCcw,
  AlertCircle,
  Copy,
  Check,
  StopCircle,
  Cpu,
  Layers,
  Flame,
  ArrowDown,
} from "lucide-react";
import { api, ChatMessagePayload } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface DisplayMessage {
  id: string;
  role: "user" | "model";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

const SAMPLE_PROMPTS = [
  "How does universal constraint satisfaction resolve resource conflicts?",
  "Analyze what causes an infeasible schedule when two departments need Room 101 at 09:00.",
  "How do ReliefOps and MedOps handle emergency supply and surgical triage?",
  "Draft an operational explanation for a published schedule revision.",
];

export function ChatPage() {
  const [messages, setMessages] = useState<DisplayMessage[]>([
    {
      id: "welcome",
      role: "model",
      content:
        "Hello! I am your AI assistant powered by **Google Gemma 4** via the official Gemini API.\n\nAsk me about timetable scheduling, constraint validation, conflict resolution, or operational logistics across our engine.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [useStreaming, setUseStreaming] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setMessages((prev) =>
      prev.map((msg) => (msg.isStreaming ? { ...msg, isStreaming: false } : msg))
    );
  };

  const handleClear = () => {
    handleStop();
    setMessages([
      {
        id: "welcome-reset",
        role: "model",
        content:
          "Conversation cleared. How can I help you today with Gemma 4 and the Gemini API?",
        timestamp: new Date(),
      },
    ]);
    setErrorMessage(null);
  };

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text || isLoading) return;

    setErrorMessage(null);
    setInput("");

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `model-${Date.now()}`;

    const newMessages: DisplayMessage[] = [
      ...messages,
      {
        id: userMsgId,
        role: "user",
        content: text,
        timestamp: new Date(),
      },
    ];

    setMessages(newMessages);
    setIsLoading(true);

    // Prepare message payload for /api/chat
    const apiPayload: ChatMessagePayload[] = newMessages
      .filter((m) => m.id !== "welcome" && m.id !== "welcome-reset")
      .map((m) => ({
        role: m.role,
        content: m.content,
      }));

    if (apiPayload.length === 0) {
      apiPayload.push({ role: "user", content: text });
    }

    if (useStreaming) {
      // Streamed response with SSE
      const controller = new AbortController();
      abortControllerRef.current = controller;

      // Add placeholder model message
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMsgId,
          role: "model",
          content: "",
          timestamp: new Date(),
          isStreaming: true,
        },
      ]);

      try {
        await api.chat.stream({
          messages: apiPayload,
          signal: controller.signal,
          onChunk: (delta: string) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, content: m.content + delta, isStreaming: true }
                  : m
              )
            );
          },
          onDone: () => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId ? { ...m, isStreaming: false } : m
              )
            );
            setIsLoading(false);
            abortControllerRef.current = null;
          },
          onError: (err: any) => {
            const errorText = err.message || "Failed to stream response from Gemma 4.";
            setErrorMessage(errorText);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId && !m.content
                  ? {
                      ...m,
                      content: `*Error communicating with Gemma 4 API: ${errorText}*`,
                      isStreaming: false,
                    }
                  : { ...m, isStreaming: false }
              )
            );
            setIsLoading(false);
            abortControllerRef.current = null;
          },
        });
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setErrorMessage(err.message || "Request failed");
        }
        setIsLoading(false);
      }
    } else {
      // Standard JSON response
      try {
        const resp = await api.chat.send(apiPayload);
        setMessages((prev) => [
          ...prev,
          {
            id: assistantMsgId,
            role: "model",
            content: resp.content,
            timestamp: new Date(),
          },
        ]);
      } catch (err: any) {
        const errorText = err.message || "Failed to fetch response from backend /api/chat.";
        setErrorMessage(errorText);
        setMessages((prev) => [
          ...prev,
          {
            id: assistantMsgId,
            role: "model",
            content: `*Error:* ${errorText}`,
            timestamp: new Date(),
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] max-w-5xl mx-auto px-4 py-3">
      {/* Top Header Card */}
      <div className="flex items-center justify-between border-b border-white/[0.08] pb-3 mb-3">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-500/20 text-white">
            <Sparkles size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold text-white tracking-tight">
                Gemma 4 AI Assistant
              </h1>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono bg-purple-500/10 text-purple-300 border border-purple-500/20">
                <Cpu size={10} />
                Gemini Cloud API
              </span>
            </div>
            <p className="text-xs text-zinc-400">
              Direct cloud inference with Google Gemma 4 (gemma-4-26b-a4b-it / gemma-4-31b-it)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Stream Toggle */}
          <button
            onClick={() => setUseStreaming(!useStreaming)}
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-all",
              useStreaming
                ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                : "bg-white/5 text-zinc-400 border-white/10 hover:text-white"
            )}
            title="Toggle between Server-Sent Events (SSE) streaming and standard JSON"
          >
            <Flame size={12} className={useStreaming ? "text-emerald-400" : ""} />
            <span>{useStreaming ? "Streaming SSE" : "Standard JSON"}</span>
          </button>

          {/* Reset button */}
          <button
            onClick={handleClear}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs text-zinc-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
            title="Clear conversation"
          >
            <RotateCcw size={12} />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="flex items-center justify-between p-3 mb-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs animate-in fade-in slide-in-from-top-1">
          <div className="flex items-center gap-2">
            <AlertCircle size={15} className="shrink-0 text-red-400" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-red-400 hover:text-red-200 text-xs px-2 py-0.5"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Messages Feed */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 scrollbar-thin scrollbar-thumb-zinc-800">
        {messages.map((msg) => {
          const isUser = msg.role === "user";
          return (
            <div
              key={msg.id}
              className={cn(
                "flex items-start gap-3 group animate-in fade-in duration-200",
                isUser ? "flex-row-reverse" : "flex-row"
              )}
            >
              {/* Avatar */}
              <div
                className={cn(
                  "h-8 w-8 rounded-xl flex items-center justify-center shrink-0 text-xs font-semibold shadow-sm",
                  isUser
                    ? "bg-white text-zinc-950"
                    : "bg-gradient-to-br from-indigo-600 to-purple-600 text-white"
                )}
              >
                {isUser ? <UserIcon size={14} /> : <Bot size={14} />}
              </div>

              {/* Message Bubble */}
              <div
                className={cn(
                  "relative max-w-[85%] md:max-w-[75%] rounded-2xl px-4 py-3 text-xs leading-relaxed",
                  isUser
                    ? "bg-white/[0.12] text-white border border-white/10 rounded-tr-sm"
                    : "bg-white/[0.04] text-zinc-200 border border-white/[0.06] rounded-tl-sm backdrop-blur-md"
                )}
              >
                {/* Content */}
                <div className="whitespace-pre-wrap font-sans selection:bg-purple-500/30">
                  {msg.content || (msg.isStreaming ? "Thinking..." : "")}
                  {msg.isStreaming && (
                    <span className="inline-block w-1.5 h-3 ml-1 bg-purple-400 animate-pulse align-middle" />
                  )}
                </div>

                {/* Footer Meta & Actions */}
                <div
                  className={cn(
                    "flex items-center gap-2 mt-2 pt-1 border-t border-white/[0.04] text-[10px] text-zinc-400",
                    isUser ? "justify-end" : "justify-between"
                  )}
                >
                  <span>
                    {msg.timestamp.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>

                  {!isUser && msg.content && (
                    <button
                      onClick={() => handleCopy(msg.id, msg.content)}
                      className="opacity-0 group-hover:opacity-100 flex items-center gap-1 text-zinc-400 hover:text-white transition-opacity"
                      title="Copy response"
                    >
                      {copiedId === msg.id ? (
                        <>
                          <Check size={11} className="text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={11} />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Loading Spinner / Typing state when starting */}
        {isLoading && !messages.some((m) => m.isStreaming && m.content) && (
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-purple-600/30 border border-purple-500/20 text-purple-300 flex items-center justify-center animate-pulse">
              <Bot size={14} />
            </div>
            <div className="px-4 py-2.5 rounded-2xl bg-white/[0.04] border border-white/[0.06] text-zinc-400 text-xs flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-purple-400 animate-bounce" />
              <span
                className="h-1.5 w-1.5 rounded-full bg-purple-400 animate-bounce"
                style={{ animationDelay: "150ms" }}
              />
              <span
                className="h-1.5 w-1.5 rounded-full bg-purple-400 animate-bounce"
                style={{ animationDelay: "300ms" }}
              />
              <span className="text-[11px] ml-1">Streaming from Google Gemini API...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Prompts (Only if only 1 welcome message) */}
      {messages.length <= 1 && (
        <div className="pt-3 pb-2">
          <div className="flex items-center gap-1.5 text-[11px] text-zinc-400 mb-2 font-medium">
            <Sparkles size={11} className="text-purple-400" />
            <span>Suggested prompts:</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {SAMPLE_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(prompt)}
                className="text-left text-xs p-2.5 rounded-xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/[0.05] hover:border-purple-500/30 text-zinc-300 hover:text-white transition-all duration-150 line-clamp-2"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat Input Bar */}
      <div className="relative pt-3 border-t border-white/[0.08] mt-2">
        <div className="relative flex items-end gap-2 bg-[#121217] border border-white/[0.12] rounded-2xl p-2 focus-within:border-purple-500/50 focus-within:ring-1 focus-within:ring-purple-500/30 transition-all shadow-xl">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type your prompt for Gemma 4 (Enter to send, Shift+Enter for new line)..."
            rows={1}
            disabled={isLoading}
            className="flex-1 bg-transparent resize-none outline-none text-xs text-white placeholder-zinc-500 px-2 py-1.5 max-h-[120px] scrollbar-thin scrollbar-thumb-zinc-800"
          />

          <div className="flex items-center gap-1 pb-0.5">
            {isLoading ? (
              <button
                onClick={handleStop}
                type="button"
                className="h-8 px-3 rounded-xl bg-red-500/20 text-red-300 border border-red-500/30 hover:bg-red-500/30 flex items-center gap-1.5 text-xs font-medium transition-all"
                title="Stop generation"
              >
                <StopCircle size={14} />
                <span>Stop</span>
              </button>
            ) : (
              <button
                onClick={() => handleSend()}
                disabled={!input.trim()}
                type="button"
                className={cn(
                  "h-8 w-8 rounded-xl flex items-center justify-center transition-all",
                  input.trim()
                    ? "bg-white text-zinc-950 hover:bg-zinc-200 shadow-md cursor-pointer"
                    : "bg-white/5 text-zinc-500 cursor-not-allowed"
                )}
                title="Send message"
              >
                <Send size={14} />
              </button>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between px-2 pt-1 text-[10px] text-zinc-400">
          <span>Backend endpoint: <code className="font-mono text-zinc-400">/api/chat</code></span>
          <span>Configurable via <code className="font-mono text-zinc-400">MODEL_NAME</code> &amp; <code className="font-mono text-zinc-400">GEMINI_API_KEY</code></span>
        </div>
      </div>
    </div>
  );
}
