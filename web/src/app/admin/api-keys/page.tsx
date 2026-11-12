"use client";

import React, { useState } from "react";
import { Key, PlusCircle, Copy, Check, Trash2, AlertTriangle, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { fmtDate } from "@/lib/format";

interface ApiKeyItem {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at?: string | null;
  status: "active" | "revoked";
}

export default function AdminApiKeysPage() {
  const [keys, setKeys] = useState<ApiKeyItem[]>([
    {
      id: "key-1",
      name: "CLI Automation Agent",
      prefix: "bsk_live_9a8f",
      created_at: new Date().toISOString(),
      last_used_at: new Date().toISOString(),
      status: "active",
    },
  ]);

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [generatedSecret, setGeneratedSecret] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCreateKey = () => {
    if (!newKeyName.trim()) {
      toast.error("Please enter a name for the API key");
      return;
    }

    const randomSuffix = Math.random().toString(36).substring(2, 10);
    const fullKey = `bsk_live_${randomSuffix}_${Math.random().toString(36).substring(2, 14)}`;
    const newPrefix = fullKey.slice(0, 14);

    const newKeyItem: ApiKeyItem = {
      id: `key-${Date.now()}`,
      name: newKeyName.trim(),
      prefix: newPrefix,
      created_at: new Date().toISOString(),
      status: "active",
    };

    setKeys((prev) => [newKeyItem, ...prev]);
    setGeneratedSecret(fullKey);
    setCreateDialogOpen(false);
    setNewKeyName("");
  };

  const handleCopy = () => {
    if (!generatedSecret) return;
    navigator.clipboard.writeText(generatedSecret);
    setCopied(true);
    toast.success("API key copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRevoke = (id: string) => {
    setKeys((prev) =>
      prev.map((k) => (k.id === id ? { ...k, status: "revoked" as const } : k))
    );
    toast.success("API key revoked");
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            API Keys & Machine Access
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            Generate and manage scoped API tokens for background automated research agents and external scrapers.
          </p>
        </div>

        <Button
          size="sm"
          variant="default"
          onClick={() => setCreateDialogOpen(true)}
          className="gap-1.5"
        >
          <PlusCircle className="size-4" />
          <span>Create New Key</span>
        </Button>
      </div>

      {/* Keys Table */}
      <Card className="p-0 overflow-hidden">
        <Table>
          <TableHeader className="bg-bg-raised/80 sticky top-0 backdrop-blur z-10">
            <TableRow>
              <TableHead className="pl-6">Key Name</TableHead>
              <TableHead>Prefix</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Last Used</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right pr-6">Action</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {keys.map((k) => (
              <TableRow key={k.id} className="hover:bg-white/[0.03]">
                <TableCell className="pl-6 font-semibold text-xs text-foreground">
                  {k.name}
                </TableCell>
                <TableCell className="font-mono text-xs text-gold-500">
                  {k.prefix}...
                </TableCell>
                <TableCell className="font-mono text-xs text-text-subtle">
                  {fmtDate(k.created_at)}
                </TableCell>
                <TableCell className="font-mono text-xs text-text-subtle">
                  {k.last_used_at ? fmtDate(k.last_used_at) : "Never"}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={k.status === "active" ? "gain" : "destructive"}
                    className="capitalize text-[10px]"
                  >
                    {k.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-right pr-6">
                  {k.status === "active" && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleRevoke(k.id)}
                      className="text-loss hover:bg-loss/10 h-8 px-2 text-xs gap-1"
                    >
                      <Trash2 className="size-3.5" />
                      <span>Revoke</span>
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Dialog 1: Create Key Input */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Generate New API Key</DialogTitle>
            <DialogDescription>
              Assign a human-readable identifier for this automated token.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
              Key Name / Purpose
            </label>
            <Input
              placeholder="e.g. Scraper Cron Worker"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              autoFocus
            />
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="default" onClick={handleCreateKey}>
              Create Key
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog 2: Secret Disclosure (Shown only once) */}
      <Dialog
        open={Boolean(generatedSecret)}
        onOpenChange={(open) => !open && setGeneratedSecret(null)}
      >
        <DialogContent className="max-w-lg border-2 border-gold-500/50">
          <DialogHeader>
            <div className="flex items-center gap-2 text-gold-500 mb-1">
              <ShieldCheck className="size-5" />
              <DialogTitle>Save Your API Key</DialogTitle>
            </div>
            <DialogDescription>
              Please copy and store this API key now. For security purposes, you will not be able to view it again.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-3">
            <div className="flex items-center justify-between p-3.5 rounded-lg bg-secondary border border-border">
              <code className="font-mono text-xs text-gold-300 break-all select-all">
                {generatedSecret}
              </code>
              <Button size="icon" variant="ghost" onClick={handleCopy} className="shrink-0 ml-2">
                {copied ? <Check className="size-4 text-gain" /> : <Copy className="size-4 text-text-subtle" />}
              </Button>
            </div>

            <div className="flex items-center gap-2 p-3 rounded-md bg-warning/10 text-warning text-xs">
              <AlertTriangle className="size-4 shrink-0" />
              <span>Keep this secret confidential. Anyone with this key can execute research runs.</span>
            </div>
          </div>

          <DialogFooter>
            <Button variant="default" onClick={() => setGeneratedSecret(null)}>
              I Have Stored the Key
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
