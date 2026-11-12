import React from "react";
import { redirect } from "next/navigation";
import { serverApi } from "@/lib/server-api";
import { AppShell } from "@/components/layout/AppShell";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const me = await serverApi("/api/v1/auth/me");
  if (!me.ok) {
    redirect("/login?next=/admin");
  }

  return <AppShell>{children}</AppShell>;
}
