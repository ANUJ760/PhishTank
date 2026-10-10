import React, { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api-client";
import { AuthLayout } from "./auth-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowLeft, CheckCircle2 } from "lucide-react";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await api.auth.forgotPassword(email);
    } catch {
      // Intentionally generic
    } finally {
      setIsLoading(false);
      setSubmitted(true);
    }
  };

  return (
    <AuthLayout>
      <div className="space-y-1 text-left mb-6">
        <h2 className="text-xl font-semibold tracking-tight text-foreground">Reset password</h2>
        <p className="text-xs text-muted-foreground">
          Enter your registered institutional email to receive reset instructions.
        </p>
      </div>

      {submitted ? (
        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800 text-xs flex items-start gap-2.5">
            <CheckCircle2 size={16} className="shrink-0 text-emerald-600 mt-0.5" />
            <div>
              <span className="font-semibold block mb-0.5">Instructions Dispatched</span>
              If an account with that email exists, password recovery details have been transmitted.
            </div>
          </div>
          <Link
            to="/auth/sign-in"
            className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline font-medium"
          >
            <ArrowLeft size={13} /> Return to sign in
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5 text-left">
            <label className="text-xs font-medium text-foreground">Institutional Email</label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="coordinator@university.edu"
              required
            />
          </div>

          <Button type="submit" isLoading={isLoading} className="w-full mt-2 h-10">
            Send Reset Instructions
          </Button>

          <div className="pt-2 text-center">
            <Link
              to="/auth/sign-in"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft size={13} /> Back to sign in
            </Link>
          </div>
        </form>
      )}
    </AuthLayout>
  );
}
