"use client";

import React from "react";
import { Download, FileJson, FileSpreadsheet, FileText } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export function ExportMenu({ briefId }: { briefId: string }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Download className="size-3.5" />
          <span>Export</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-44 p-1.5 glass space-y-1">
        <a
          href={`/api/proxy/api/v1/exports/brief/${briefId}.pdf`}
          download
          className="flex items-center gap-2.5 px-3 py-2 text-xs rounded-md text-foreground hover:bg-white/5 transition-colors"
        >
          <FileText className="size-4 text-gold-500" />
          <span>Download PDF</span>
        </a>
        <a
          href={`/api/proxy/api/v1/exports/brief/${briefId}.json`}
          download
          className="flex items-center gap-2.5 px-3 py-2 text-xs rounded-md text-foreground hover:bg-white/5 transition-colors"
        >
          <FileJson className="size-4 text-info" />
          <span>Download JSON</span>
        </a>
        <a
          href={`/api/proxy/api/v1/exports/brief/${briefId}.csv`}
          download
          className="flex items-center gap-2.5 px-3 py-2 text-xs rounded-md text-foreground hover:bg-white/5 transition-colors"
        >
          <FileSpreadsheet className="size-4 text-gain" />
          <span>Download CSV</span>
        </a>
      </PopoverContent>
    </Popover>
  );
}
