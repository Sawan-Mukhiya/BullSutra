"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Eye, EyeOff, AlertCircle, ArrowRight, ShieldCheck } from "lucide-react";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useLogin } from "@/hooks/useSession";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
  remember: z.boolean().default(false),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  return (
    <React.Suspense fallback={<div className="min-h-screen bg-background" />}>
      <LoginPageContent />
    </React.Suspense>
  );
}

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") || "/admin";

  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loginMutation = useLogin();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema as any),
    defaultValues: { email: "", password: "", remember: true },
  });

  const onSubmit = async (data: LoginFormValues) => {
    setErrorMsg(null);
    try {
      await loginMutation.mutateAsync({
        email: data.email,
        password: data.password,
      });
      // Validate next redirect url: must start with / and not //
      const safeNext = next.startsWith("/") && !next.startsWith("//") ? next : "/admin";
      router.replace(safeNext);
    } catch (err: any) {
      setErrorMsg(err?.message || "Invalid email or password");
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background text-foreground">
      {/* Left Brand Panel (Desktop only) */}
      <div className="relative hidden lg:flex flex-col justify-between p-12 bg-secondary/30 border-r border-border overflow-hidden grid-texture">
        <div className="flex items-center gap-3">
          <div className="size-10 rounded-full bg-gold-gradient flex items-center justify-center shadow-md">
            <svg viewBox="0 0 24 24" className="size-5 fill-primary-foreground stroke-primary-foreground stroke-[1.5]">
              <path d="M4 18 C4 18 8 16 12 10 C16 4 20 4 20 4 M20 4 L16 8 M20 4 L20 9" />
            </svg>
          </div>
          <span className="font-display text-2xl font-bold tracking-tight">
            Bull<span className="text-gold-500">Sutra</span>
          </span>
        </div>

        <div className="space-y-4 max-w-md my-auto">
          <blockquote className="font-display text-3xl font-bold tracking-tight leading-snug">
            &ldquo;Clarity and mathematical discipline before every market decision.&rdquo;
          </blockquote>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Deterministic multi-agent reasoning, point-in-time financial causality, and zero hallucinated quantitative metrics.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-text-subtle font-mono">
          <ShieldCheck className="size-4 text-gain" />
          <span>Argon2id & JWT Authenticated Backend Gateway</span>
        </div>
      </div>

      {/* Right Form Panel */}
      <div className="relative flex items-center justify-center p-6 sm:p-12">
        <div className="absolute top-6 right-6">
          <ThemeToggle />
        </div>

        <Card featured className="w-full max-w-[440px] p-8 sm:p-10 rounded-2xl space-y-6">
          <div>
            <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Welcome back
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1">
              Sign in to access agent runners, pipeline management, and exports.
            </p>
          </div>

          {errorMsg && (
            <div className="p-3.5 rounded-lg bg-loss/15 border border-loss/40 text-loss text-xs flex items-center gap-2">
              <AlertCircle className="size-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground uppercase tracking-wider">
                Email Address
              </label>
              <Input
                type="email"
                placeholder="admin@bullsutra.com"
                autoComplete="email"
                error={Boolean(errors.email)}
                {...register("email")}
              />
              {errors.email && (
                <span className="text-xs text-loss">{errors.email.message}</span>
              )}
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-foreground uppercase tracking-wider">
                  Password
                </label>
              </div>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••••••"
                  autoComplete="current-password"
                  error={Boolean(errors.password)}
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-subtle hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              {errors.password && (
                <span className="text-xs text-loss">{errors.password.message}</span>
              )}
            </div>

            <Button
              type="submit"
              className="w-full h-11 text-sm font-semibold mt-2"
              loading={loginMutation.isPending}
            >
              Sign In to Platform
            </Button>
          </form>

          {/* Switch to Sign Up */}
          <div className="pt-4 border-t border-border/60 text-center space-y-3">
            <p className="text-xs text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link
                href={`/signup${next ? `?next=${encodeURIComponent(next)}` : ""}`}
                className="font-semibold text-gold-500 hover:text-gold-300 transition-colors"
              >
                Create Account
              </Link>
            </p>

            <div>
              <Link
                href="/dashboard"
                className="text-xs text-text-subtle hover:text-foreground transition-colors inline-flex items-center gap-1"
              >
                <span>Continue to Public Research Dashboard</span>
                <ArrowRight className="size-3" />
              </Link>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
