import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import { AuthLayout } from "./auth-layout";
import { Eye, EyeOff } from "lucide-react";

export function SignInPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("admin@gecompose.internal");
  const [password, setPassword] = useState("password123");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      await signIn(email, password);
      const from = (location.state as any)?.from?.pathname || "/app/dashboard";
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err?.message || "Invalid credentials. Please verify your email and password.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <div className="space-y-1 text-left mb-6">
        <h2 className="text-xl font-semibold tracking-tight text-white">Welcome back</h2>
        <p className="text-xs text-zinc-400">
          Enter your institutional credentials to access the scheduling workspace.
        </p>
      </div>

      <div className="mb-5 p-3 rounded-xl bg-white/[0.03] border border-white/5 text-xs text-zinc-400 flex flex-col gap-1 text-left">
        <span className="font-semibold text-white">Quick Demo Credentials:</span>
        <div className="flex justify-between items-center text-[11px] font-mono mt-1">
          <span className="text-zinc-300">admin@gecompose.internal</span>
          <span className="bg-zinc-800 text-zinc-200 px-1.5 py-0.5 rounded-md border border-white/5">password123</span>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-xl bg-white/[0.04] border border-white/10 text-xs text-zinc-300 text-left">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5 text-left">
          <label className="text-xs font-medium text-zinc-300">Institutional Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="coordinator@gecompose.internal"
            className="w-full h-10 px-3.5 rounded-xl bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
            required
          />
        </div>

        <div className="space-y-1.5 text-left">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-zinc-300">Password</label>
            <Link
              to="/auth/forgot-password"
              className="text-xs text-zinc-400 hover:text-white transition-colors"
            >
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full h-10 px-3.5 pr-10 rounded-xl bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
            >
              {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full h-10 rounded-full bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all shadow-sm active:scale-[0.98] disabled:opacity-50 mt-2"
        >
          {isLoading ? "Signing in..." : "Sign in to workspace"}
        </button>
      </form>

      <div className="mt-6 text-center text-xs text-zinc-400">
        Don&apos;t have an institutional account?{" "}
        <Link to="/auth/sign-up" className="text-white font-medium hover:underline">
          Sign up
        </Link>
      </div>
    </AuthLayout>
  );
}
