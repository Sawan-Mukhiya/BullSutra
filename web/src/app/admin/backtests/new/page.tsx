"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { FlaskConical, Play } from "lucide-react";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { RunProgress } from "@/components/jobs/RunProgress";
import { useCreateBacktest } from "@/hooks/useBacktest";

const backtestFormSchema = z.object({
  name: z.string().min(3, "Name must be at least 3 characters").max(80),
  train_days: z.number().min(250).max(2000),
  test_days: z.number().min(20).max(500),
  embargo_days: z.number().min(0).max(60),
  horizon: z.number().min(1).max(60),
  initial_capital: z.number().min(100000),
  max_positions: z.number().min(1).max(40),
  slippage_bps: z.number().min(0).max(200),
  min_calibrated_confidence: z.number().min(0).max(1),
  rf_annual: z.number().min(0).max(0.3),
  apply_taxes: z.boolean(),
  bootstrap_samples: z.number().min(200).max(10000),
});

type BacktestFormValues = z.infer<typeof backtestFormSchema>;

export default function NewBacktestPage() {
  const router = useRouter();
  const createBacktest = useCreateBacktest();
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<BacktestFormValues>({
    resolver: zodResolver(backtestFormSchema as any),
    defaultValues: {
      name: `Walk-Forward Run ${new Date().toISOString().slice(0, 10)}`,
      train_days: 750,
      test_days: 120,
      embargo_days: 10,
      horizon: 10,
      initial_capital: 1000000,
      max_positions: 10,
      slippage_bps: 10,
      min_calibrated_confidence: 0.55,
      rf_annual: 0.06,
      apply_taxes: true,
      bootstrap_samples: 1000,
    },
  });

  const applyTaxes = watch("apply_taxes");

  const onSubmit = async (values: BacktestFormValues) => {
    try {
      const { name, ...configValues } = values;
      const payload = {
        name,
        config: {
          ...configValues,
          step_days: values.test_days,
          execution: "next_open",
          strategies: [
            "full",
            "tech_only",
            "fund_only",
            "news_only",
            "consensus_basic",
            "consensus_weighted",
            "consensus_debate",
            "bh_equal_weight",
            "bh_nepse_index",
          ],
        },
      };

      const res = await createBacktest.mutateAsync(payload);
      toast.success("Backtest simulation queued!");
      if (res.job_id) {
        setActiveJobId(res.job_id);
      } else {
        router.push(`/backtests/${res.backtest_id}`);
      }
    } catch (err: any) {
      toast.error(err?.message || "Failed to create backtest run");
    }
  };

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      <div>
        <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          Configure Walk-Forward Backtest
        </h1>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          Simulate deterministic trading strategies across historical NEPSE rolling folds with real execution slabs.
        </p>
      </div>

      <Card featured className="p-6 lg:p-8 space-y-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Backtest Run Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
              Simulation Run Name
            </label>
            <Input
              placeholder="e.g. 5-Year Full Walk-Forward Benchmark"
              {...register("name")}
              error={Boolean(errors.name)}
            />
            {errors.name && <span className="text-xs text-loss">{errors.name.message}</span>}
          </div>

          {/* Rolling Folds Window Configuration */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
                Train Window (Days)
              </label>
              <Input
                type="number"
                {...register("train_days", { valueAsNumber: true })}
                className="font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
                Test Window (Days)
              </label>
              <Input
                type="number"
                {...register("test_days", { valueAsNumber: true })}
                className="font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
                Embargo (Days)
              </label>
              <Input
                type="number"
                {...register("embargo_days", { valueAsNumber: true })}
                className="font-mono"
              />
            </div>
          </div>

          {/* Portfolio & Sizing Parameters */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
                Initial Capital (NPR)
              </label>
              <Input
                type="number"
                step="50000"
                {...register("initial_capital", { valueAsNumber: true })}
                className="font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
                Max Concurrent Positions
              </label>
              <Input
                type="number"
                {...register("max_positions", { valueAsNumber: true })}
                className="font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
                Execution Slippage (bps)
              </label>
              <Input
                type="number"
                {...register("slippage_bps", { valueAsNumber: true })}
                className="font-mono"
              />
            </div>
          </div>

          {/* Thresholds & Regulatory Assumptions */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-border/60">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
                Min Calibrated Confidence (0.0 to 1.0)
              </label>
              <Input
                type="number"
                step="0.05"
                {...register("min_calibrated_confidence", { valueAsNumber: true })}
                className="font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
                Bootstrap Samples
              </label>
              <Input
                type="number"
                step="100"
                {...register("bootstrap_samples", { valueAsNumber: true })}
                className="font-mono"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <label className="flex items-center gap-2.5 cursor-pointer text-xs font-medium">
              <Switch
                checked={applyTaxes}
                onCheckedChange={(c) => setValue("apply_taxes", c)}
              />
              <span>Deduct Capital Gains Tax (7.5% short-term / 5.0% long-term)</span>
            </label>
          </div>

          <Button
            type="submit"
            size="lg"
            className="w-full gap-2 text-sm font-semibold"
            loading={createBacktest.isPending}
          >
            <Play className="size-4" />
            <span>Launch Walk-Forward Simulation</span>
          </Button>
        </form>
      </Card>

      {/* Live SSE Stepper */}
      {activeJobId && (
        <RunProgress
          jobId={activeJobId}
          kind="backtest"
          onFinished={(res) => {
            if (res.backtest_id) {
              router.push(`/backtests/${res.backtest_id}`);
            }
          }}
        />
      )}
    </div>
  );
}
