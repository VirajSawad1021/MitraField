"use client";

import { AppShell } from "@/components/AppShell";
import { ProjectGrid } from "@/components/ProjectGrid";
import { Eyebrow } from "@/components/ui";

export default function ProjectsPage() {
  return (
    <AppShell>
      <main className="mx-auto max-w-[1240px] px-5 pb-24 pt-10 sm:px-8">
        <div className="mb-8">
          <Eyebrow>Workspace</Eyebrow>
          <h1 className="mt-1.5 text-[32px] font-semibold tracking-tight">Projects</h1>
          <p className="mt-1.5 text-[14px] text-body">Open a video to watch it, change a scene or make a new language version.</p>
        </div>
        <ProjectGrid />
      </main>
    </AppShell>
  );
}
