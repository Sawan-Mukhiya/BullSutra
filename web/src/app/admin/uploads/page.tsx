"use client";

import React, { useState } from "react";
import { UploadCloud, FileText, CheckCircle2, AlertTriangle, ArrowRight, Download } from "lucide-react";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function AdminUploadsPage() {
  const [uploadType, setUploadType] = useState<"prices" | "fundamentals">("fundamentals");
  const [file, setFile] = useState<File | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [validationResult, setValidationResult] = useState<any | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0];
      if (f.size > 20 * 1024 * 1024) {
        toast.error("File exceeds maximum allowed size of 20MB");
        return;
      }
      setFile(f);
      setValidationResult(null);
    }
  };

  const handleValidate = async () => {
    if (!file) return;
    setIsValidating(true);
    setValidationResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`/api/proxy/api/v1/uploads/${uploadType}/validate`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || "Validation failed");
      }

      setValidationResult(data);
      if (data.error_count === 0) {
        toast.success(`Validated ${data.row_count} rows with zero errors`);
      } else {
        toast.warning(`Validation completed with ${data.error_count} row errors`);
      }
    } catch (err: any) {
      toast.error(err?.message || "Failed to validate file");
    } finally {
      setIsValidating(false);
    }
  };

  const handleCommit = async () => {
    if (!validationResult?.upload_id) return;
    setIsCommitting(true);

    try {
      const res = await fetch(`/api/proxy/api/v1/uploads/${validationResult.upload_id}/commit`, {
        method: "POST",
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || "Commit failed");
      }

      toast.success(`Successfully committed ${data.rows_inserted ?? data.row_count} records to database!`);
      setFile(null);
      setValidationResult(null);
    } catch (err: any) {
      toast.error(err?.message || "Failed to commit upload");
    } finally {
      setIsCommitting(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          Analytical Data Upload Wizard
        </h1>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          Validate and commit quarterly company financials or historical daily prices directly into PostgreSQL.
        </p>
      </div>

      {/* Step 1 & 2 Card */}
      <Card featured className="p-6 lg:p-8 space-y-6">
        {/* Type Selection */}
        <div className="space-y-3">
          <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
            1. Select Dataset Target
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => {
                setUploadType("fundamentals");
                setValidationResult(null);
              }}
              className={`p-4 rounded-xl border text-left transition-all ${
                uploadType === "fundamentals"
                  ? "bg-accent/40 border-gold-500 shadow-sm"
                  : "bg-secondary/40 border-border text-muted-foreground hover:bg-secondary/70"
              }`}
            >
              <div className="font-semibold text-sm text-foreground flex items-center justify-between">
                <span>Quarterly Financials CSV</span>
                {uploadType === "fundamentals" && <CheckCircle2 className="size-4 text-gold-500" />}
              </div>
              <p className="text-xs text-text-subtle mt-1">
                EPS, BVPS, ROE, NPL, CAR, and net profit with point-in-time usable_from.
              </p>
            </button>

            <button
              type="button"
              onClick={() => {
                setUploadType("prices");
                setValidationResult(null);
              }}
              className={`p-4 rounded-xl border text-left transition-all ${
                uploadType === "prices"
                  ? "bg-accent/40 border-gold-500 shadow-sm"
                  : "bg-secondary/40 border-border text-muted-foreground hover:bg-secondary/70"
              }`}
            >
              <div className="font-semibold text-sm text-foreground flex items-center justify-between">
                <span>Daily OHLCV Prices CSV</span>
                {uploadType === "prices" && <CheckCircle2 className="size-4 text-gold-500" />}
              </div>
              <p className="text-xs text-text-subtle mt-1">
                EOD price bars with high/low/close and traded volume.
              </p>
            </button>
          </div>
        </div>

        {/* Template Download Link */}
        {uploadType === "fundamentals" && (
          <div className="flex items-center justify-between p-3.5 rounded-lg bg-secondary/50 border border-border text-xs">
            <span className="text-muted-foreground">Standardized template with canonical schema columns</span>
            <a
              href="/templates/fundamentals_template.csv"
              download
              className="inline-flex items-center gap-1.5 font-semibold text-gold-500 hover:text-gold-300 transition-colors"
            >
              <Download className="size-3.5" />
              <span>Download Template</span>
            </a>
          </div>
        )}

        {/* File Dropzone */}
        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
            2. Choose CSV File (Max 20MB)
          </label>
          <div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-gold-500/50 transition-colors bg-secondary/20">
            <UploadCloud className="size-8 mx-auto text-gold-500 mb-2" />
            <input
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="text-xs font-mono text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-primary file:text-primary-foreground hover:file:opacity-90"
            />
          </div>
        </div>

        {/* Action Button */}
        <Button
          size="lg"
          onClick={handleValidate}
          disabled={!file || isValidating}
          loading={isValidating}
          className="w-full text-sm font-semibold"
        >
          <span>Validate CSV Ingestion Rules</span>
        </Button>
      </Card>

      {/* Step 3: Validation Results & Commit */}
      {validationResult && (
        <Card className="p-6 lg:p-8 space-y-6">
          <div className="flex items-center justify-between border-b border-border/80 pb-4">
            <div>
              <h3 className="font-display font-semibold text-lg text-foreground">
                Validation Report
              </h3>
              <p className="text-xs text-muted-foreground font-mono mt-0.5">
                Total rows parsed: {validationResult.row_count} • Errors: {validationResult.error_count}
              </p>
            </div>

            {validationResult.error_count === 0 ? (
              <Badge variant="gain" className="text-xs gap-1.5 py-1 px-3">
                <CheckCircle2 className="size-3.5" />
                Schema Validated
              </Badge>
            ) : (
              <Badge variant="destructive" className="text-xs gap-1.5 py-1 px-3">
                <AlertTriangle className="size-3.5" />
                Has Schema Errors
              </Badge>
            )}
          </div>

          {/* Errors Table if any */}
          {validationResult.errors && validationResult.errors.length > 0 && (
            <div className="space-y-2">
              <span className="text-xs font-semibold text-loss uppercase tracking-wider block">
                Validation Errors (First {validationResult.errors.length})
              </span>
              <div className="max-h-48 overflow-y-auto border border-loss/30 rounded-lg">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Row #</TableHead>
                      <TableHead>Field</TableHead>
                      <TableHead>Error Description</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {validationResult.errors.map((err: any, idx: number) => (
                      <TableRow key={idx} className="text-xs font-mono text-loss">
                        <TableCell>{err.row ?? err.line}</TableCell>
                        <TableCell>{err.field}</TableCell>
                        <TableCell>{err.message}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

          {/* Commit Action */}
          <div className="pt-4 border-t border-border flex items-center justify-between">
            <p className="text-xs text-text-subtle">
              {validationResult.error_count === 0
                ? "Data passed all schema, type, and causality checks."
                : "Resolve row errors before committing to database."}
            </p>

            <Button
              size="lg"
              variant="default"
              disabled={validationResult.error_count > 0 || isCommitting}
              loading={isCommitting}
              onClick={handleCommit}
              className="gap-2 text-sm font-semibold"
            >
              <span>Commit Records to Database</span>
              <ArrowRight className="size-4" />
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
