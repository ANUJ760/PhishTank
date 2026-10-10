import React, { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import { AuthLayout } from "./auth-layout";
import {
  Eye,
  EyeOff,
  UserCheck,
  ShieldCheck,
  GraduationCap,
  Sparkles,
  ArrowRight,
  LogIn,
  RefreshCw,
  CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";

interface DemoAccount {
  name: string;
  email: string;
  role: string;
  badge: string;
  icon: React.ElementType;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    name: "Demo Coordinator",
    email: "admin@gecompose.internal",
    role: "Coordinator",
    badge: "Full Admin",
    icon: ShieldCheck,
  },
  {
    name: "Prof. Rao",
    email: "rao@gecompose.internal",
    role: "Reviewer",
    badge: "Faculty Lead",
    icon: GraduationCap,
  },
  {
    name: "Prof. Mehta",
    email: "mehta@gecompose.internal",
    role: "Reviewer",
    badge: "Faculty",
    icon: UserCheck,
  },
  {
    name: "Dean Academics",
    email: "dean@gecompose.internal",
    role: "Reviewer",
    badge: "Approver",
    icon: ShieldCheck,
  },
];

export function SignInPage() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("admin@gecompose.internal");
  const [password, setPassword] = useState("password123");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const destination = (location.state as any)?.from?.pathname || "/app/dashboard";

  // Redirect if already authenticated
  useEffect(() => {
    if (user) {
      navigate(destination, { replace: true });
    }
  }, [user, navigate, destination]);

  const handleExecuteSignIn = async (signInEmail: string, signInPass: string) => {
    setError(null);
    setIsLoading(true);
    try {
      const loggedUser = await signIn(signInEmail, signInPass);
      toast.success(`Welcome back, ${loggedUser.name}!`);
      navigate(destination, { replace: true });
    } catch (err: any) {
      setError(err?.message || "Invalid credentials. Please verify your email and password.");
      toast.error("Sign in failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await handleExecuteSignIn(email, password);
  };

  const handleSelectQuickAccount = async (acc: DemoAccount) => {
    setEmail(acc.email);
    setPassword("password123");
    await handleExecuteSignIn(acc.email, "password123");
  };

  return (
    <AuthLayout>
      <div className="space-y-1 text-left mb-6">
        <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          <LogIn size={20} className="text-zinc-200" />
          Institutional Sign In
        </h2>
        <p className="text-xs text-zinc-400">
          Enter institutional credentials to manage constraint optimization and timetables.
        </p>
      </div>

      {/* 1-Click Institutional Demo Accounts */}
      <div className="mb-6 space-y-2 text-left">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-zinc-300 flex items-center gap-1.5">
            <Sparkles size={12} className="text-amber-400" />
            1-Click Institutional Access:
          </span>
          <span className="text-[10px] text-zinc-500 font-mono">Instant Sign In</span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {DEMO_ACCOUNTS.map((acc) => {
            const Icon = acc.icon;
            const isSelected = email === acc.email;
            return (
              <button
                key={acc.email}
                type="button"
                disabled={isLoading}
                onClick={() => handleSelectQuickAccount(acc)}
                className={`p-2.5 rounded-lg border text-left transition-all relative overflow-hidden group ${
                  isSelected
                    ? "bg-white/[0.08] border-white/20 text-white shadow-sm"
                    : "bg-white/[0.02] hover:bg-white/[0.05] border-white/5 hover:border-white/10 text-zinc-300"
                }`}
              >
                <div className="flex items-center justify-between">
                  <Icon size={13} className="text-zinc-400 group-hover:text-white transition-colors" />
                  <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300">
                    {acc.badge}
                  </span>
                </div>
                <p className="font-semibold text-xs text-white mt-1.5 truncate">{acc.name}</p>
                <p className="text-[10px] text-zinc-500 font-mono truncate">{acc.email}</p>
              </button>
            );
          })}
        </div>
      </div>

      <div className="relative my-4 flex items-center justify-center">
        <div className="border-t border-white/10 w-full" />
        <span className="bg-[#121217] px-2 text-[10px] font-mono text-zinc-500 uppercase tracking-wider relative shrink-0">
          Or Enter Credentials
        </span>
        <div className="border-t border-white/10 w-full" />
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-md bg-red-950/20 border border-red-500/20 text-xs text-red-300 text-left">
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
            className="w-full h-10 px-3.5 rounded-md bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
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
              className="w-full h-10 px-3.5 pr-10 rounded-md bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
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
          className="w-full h-10 rounded-md bg-white text-zinc-950 font-semibold text-xs hover:bg-zinc-200 transition-all shadow-sm active:scale-[0.98] disabled:opacity-50 mt-2 flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <RefreshCw size={13} className="animate-spin" />
              <span>Signing in...</span>
            </>
          ) : (
            <>
              <span>Sign in to Workspace</span>
              <ArrowRight size={13} />
            </>
          )}
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
