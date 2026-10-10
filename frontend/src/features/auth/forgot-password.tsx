import React, { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api-client";
import { AuthLayout } from "./auth-layout";
import { ArrowLeft } from "lucide-react";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      await api.auth.forgotPassword(email);
      setSubmitted(true);
    } catch (err: any) {
      setError(err?.message || "Password reset request failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <div className="space-y-1 text-left mb-6">
        <h2 className="text-xl font-semibold tracking-tight text-white">Reset password</h2>
        <p className="text-xs text-zinc-400">
          Enter your email to receive recovery instructions.
        </p>
      </div>

      {submitted ? (
        <div className="space-y-4 text-left">
          <div className="p-3.5 rounded-md border border-white/10 bg-white/[0.03] text-xs text-zinc-300">
            If an account exists for <strong className="text-white">{email}</strong>, a reset link has been dispatched to your institutional inbox.
          </div>
          <Link
            to="/auth/sign-in"
            className="inline-flex items-center gap-1.5 text-xs text-white hover:underline pt-2 font-medium"
          >
            <ArrowLeft size={13} />
            <span>Back to sign in</span>
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4 text-left">
          {error && (
            <div className="p-3 rounded-md bg-white/[0.04] border border-white/10 text-xs text-zinc-300">
              {error}
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-300">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="coordinator@gecompose.internal"
              className="w-full h-10 px-3.5 rounded-md bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full h-10 rounded-md bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all shadow-sm active:scale-[0.98] disabled:opacity-50 mt-2"
          >
            {isLoading ? "Sending..." : "Send Reset Instructions"}
          </button>

          <div className="text-center pt-2">
            <Link
              to="/auth/sign-in"
              className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-white transition-colors"
            >
              <ArrowLeft size={12} />
              <span>Back to sign in</span>
            </Link>
          </div>
        </form>
      )}
    </AuthLayout>
  );
}
