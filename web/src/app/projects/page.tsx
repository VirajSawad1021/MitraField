"use client";

import { Plus } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { ProjectGrid } from "@/components/ProjectGrid";
import { Eyebrow, LinkButton } from "@/components/ui";

export default function ProjectsPage() {
  return (
    <AppShell>
      <main className="mx-auto max-w-[1240px] px-5 pb-24 pt-10 sm:px-8">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <Eyebrow>Workspace</Eyebrow>
            <h1 className="mt-1.5 text-[32px] font-semibold tracking-tight">Projects</h1>
          </div>
          <LinkButton href="/new"><Plus className="h-4 w-4" />New video</LinkButton>
        </div>
        <ProjectGrid />
      </main>
    </AppShell>
  );
}
