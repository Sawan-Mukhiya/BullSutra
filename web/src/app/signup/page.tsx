"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Eye, EyeOff, AlertCircle, ArrowRight, ShieldCheck, Check, Sparkles } from "lucide-react";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSignup } from "@/hooks/useSession";

const signupSchema = z
  .object({
    email: z.string().email("Please enter a valid email address"),
    password: z.string().min(8, "Password must be at least 8 characters long"),
    confirmPassword: z.string().min(1, "Please confirm your password"),
    agreeTerms: z.boolean().refine((val) => val === true, {
      message: "You must acknowledge the quantitative risk disclaimer to proceed",
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type SignupFormValues = z.infer<typeof signupSchema>;

export default function SignupPage() {
  return (
    <React.Suspense fallback={<div className="min-h-screen bg-background" />}>
      <SignupPageContent />
    </React.Suspense>
  );
}

function SignupPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") || "/admin";

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const signupMutation = useSignup();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema as any),
    defaultValues: {
      email: "",
      password: "",
      confirmPassword: "",
      agreeTerms: false,
    },
  });

  const passwordValue = watch("password") || "";
  const hasMinLength = passwordValue.length >= 8;

  const onSubmit = async (data: SignupFormValues) => {
    setErrorMsg(null);
    try {
      await signupMutation.mutateAsync({
        email: data.email,
        password: data.password,
      });
      const safeNext = next.startsWith("/") && !next.startsWith("//") ? next : "/admin";
      router.replace(safeNext);
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to create account. Please try again.");
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background text-foreground">
      {/* Left Brand Panel (Desktop only) */}
      <div className="relative hidden lg:flex flex-col justify-between p-12 bg-secondary/30 border-r border-border overflow-hidden grid-texture">
        <div className="flex items-center gap-3">
          <div className="size-10 rounded-full bg-gold-gradient flex items-center justify-center shadow-md">
            <svg
              viewBox="0 0 24 24"
              className="size-5 fill-primary-foreground stroke-primary-foreground stroke-[1.5]"
            >
              <path d="M4 18 C4 18 8 16 12 10 C16 4 20 4 20 4 M20 4 L16 8 M20 4 L20 9" />
            </svg>
          </div>
          <span className="font-display text-2xl font-bold tracking-tight">
            Bull<span className="text-gold-500">Sutra</span>
          </span>
        </div>

        <div className="space-y-4 max-w-md my-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gold-500/10 border border-gold-500/20 text-gold-500 text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="size-3.5" />
            <span>Institutional Multi-Agent Access</span>
          </div>

          <blockquote className="font-display text-3xl font-bold tracking-tight leading-snug">
            &ldquo;Empowering rigorous Nepal stock analytics with zero lookahead bias.&rdquo;
          </blockquote>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Create an account to run the 11-node LangGraph pipeline, orchestrate walk-forward backtests, and export audit-ready research dossiers.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-text-subtle font-mono">
          <ShieldCheck className="size-4 text-gain" />
          <span>Argon2id Salted Hashes & HttpOnly Token Storage</span>
        </div>
      </div>

      {/* Right Form Panel */}
      <div className="relative flex items-center justify-center p-6 sm:p-12 overflow-y-auto">
        <div className="absolute top-6 right-6">
          <ThemeToggle />
        </div>

        <Card featured className="w-full max-w-[460px] p-8 sm:p-10 rounded-2xl space-y-6 my-auto">
          <div>
            <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Create an account
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1">
              Join BullSutra to manage pipelines, execute agent runs, and evaluate strategies.
            </p>
          </div>

          {errorMsg && (
            <div className="p-3.5 rounded-lg bg-loss/15 border border-loss/40 text-loss text-xs flex items-center gap-2">
              <AlertCircle className="size-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Email Address */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground uppercase tracking-wider">
                Email Address
              </label>
              <Input
                type="email"
                placeholder="analyst@bullsutra.com"
                autoComplete="email"
                error={Boolean(errors.email)}
                {...register("email")}
              />
              {errors.email && (
                <span className="text-xs text-loss">{errors.email.message}</span>
              )}
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-foreground uppercase tracking-wider">
                  Password
                </label>
                <span className="text-[11px] text-text-subtle font-mono">Min. 8 characters</span>
              </div>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••••••"
                  autoComplete="new-password"
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

            {/* Confirm Password */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground uppercase tracking-wider">
                Confirm Password
              </label>
              <div className="relative">
                <Input
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="••••••••••••"
                  autoComplete="new-password"
                  error={Boolean(errors.confirmPassword)}
                  {...register("confirmPassword")}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-subtle hover:text-foreground"
                >
                  {showConfirmPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              {errors.confirmPassword && (
                <span className="text-xs text-loss">{errors.confirmPassword.message}</span>
              )}
            </div>

            {/* Password validation pill */}
            <div className="flex items-center gap-2 pt-1 text-xs">
              <span
                className={`size-4 rounded-full flex items-center justify-center text-[10px] ${
                  hasMinLength
                    ? "bg-gain/20 text-gain border border-gain/40"
                    : "bg-secondary text-text-subtle border border-border"
                }`}
              >
                {hasMinLength ? <Check className="size-2.5" /> : "•"}
              </span>
              <span className={hasMinLength ? "text-gain font-medium" : "text-text-subtle"}>
                Password length satisfies 8-character security threshold
              </span>
            </div>

            {/* Terms / Disclaimer Checkbox */}
            <div className="pt-2">
              <label className="flex items-start gap-2.5 cursor-pointer text-xs text-muted-foreground leading-relaxed">
                <input
                  type="checkbox"
                  className="mt-0.5 rounded border-border bg-secondary text-gold-500 focus:ring-gold-500 size-4 shrink-0"
                  {...register("agreeTerms")}
                />
                <span>
                  I understand that BullSutra is an algorithmic research platform and agree that quantitative scores and backtests do not constitute investment advice.
                </span>
              </label>
              {errors.agreeTerms && (
                <span className="text-xs text-loss block mt-1">{errors.agreeTerms.message}</span>
              )}
            </div>

            <Button
              type="submit"
              className="w-full h-11 text-sm font-semibold mt-4"
              loading={signupMutation.isPending}
            >
              Create BullSutra Account
            </Button>
          </form>

          {/* Switch to Sign In */}
          <div className="pt-4 border-t border-border/60 text-center space-y-3">
            <p className="text-xs text-muted-foreground">
              Already have an account?{" "}
              <Link
                href={`/login${next ? `?next=${encodeURIComponent(next)}` : ""}`}
                className="font-semibold text-gold-500 hover:text-gold-300 transition-colors"
              >
                Sign In
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
