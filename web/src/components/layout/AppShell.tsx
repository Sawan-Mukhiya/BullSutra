"use client";

import React from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { BottomTabBar } from "./BottomTabBar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Sidebar />
      <div className="flex-1 md:pl-[76px] lg:pl-[264px] flex flex-col min-w-0 transition-all">
        <TopBar />
        <main className="flex-1 max-w-[1440px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8 pb-24 md:pb-12">
          {children}
        </main>
      </div>
      <BottomTabBar />
    </div>
  );
}
