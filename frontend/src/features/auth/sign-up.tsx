import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import { AuthLayout } from "./auth-layout";

export function SignUpPage() {
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }
    setIsLoading(true);
    try {
      await signUp(name, email, password);
      navigate("/app/dashboard", { replace: true });
    } catch (err: any) {
      setError(err?.message || "Registration failed. Please verify your details.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <div className="space-y-1 text-left mb-6">
        <h2 className="text-xl font-semibold tracking-tight text-white">Create an account</h2>
        <p className="text-xs text-zinc-400">
          Register an institutional identity for constraint management and reviews.
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-md bg-white/[0.04] border border-white/10 text-xs text-zinc-300 text-left">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4 text-left">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-300">Full Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Prof. Jane Doe"
            className="w-full h-10 px-3.5 rounded-md bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
            required
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-300">Email Address</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="jane@gecompose.internal"
            className="w-full h-10 px-3.5 rounded-md bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
            required
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-300">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full h-10 px-3.5 rounded-md bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
            required
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-300">Confirm Password</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full h-10 px-3.5 rounded-md bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
            required
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full h-10 rounded-md bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all shadow-sm active:scale-[0.98] disabled:opacity-50 mt-2"
        >
          {isLoading ? "Creating account..." : "Register Account"}
        </button>
      </form>

      <div className="mt-6 text-center text-xs text-zinc-400">
        Already registered?{" "}
        <Link to="/auth/sign-in" className="text-white font-medium hover:underline">
          Sign in
        </Link>
      </div>
    </AuthLayout>
  );
}
