"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { ProjectGrid } from "@/components/ProjectGrid";
import { Studio } from "@/components/studio/Studio";
import { Eyebrow, LinkButton } from "@/components/ui";

export default function StudioPage() {
  return (
    <AppShell wide>
      <Suspense>
        <Inner />
      </Suspense>
    </AppShell>
  );
}

function Inner() {
  const id = useSearchParams().get("p");
  if (!id) {
    return (
      <main className="mx-auto max-w-[1240px] px-5 pb-24 pt-10 sm:px-8">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <Eyebrow>Studio</Eyebrow>
            <h1 className="mt-1.5 text-[32px] font-semibold tracking-tight">Open a project</h1>
            <p className="mt-1.5 text-[14px] text-body">Pick a video to edit its beats, or start a new one.</p>
          </div>
          <LinkButton href="/new">New video</LinkButton>
        </div>
        <ProjectGrid />
      </main>
    );
  }
  return <Studio id={id} />;
}
