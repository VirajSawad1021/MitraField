"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { Studio } from "@/components/studio/Studio";
import { Empty, LinkButton } from "@/components/ui";

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
      <main className="mx-auto max-w-xl px-5 py-20">
        <Empty title="No project selected" body="Open a project or start a new video." action={<LinkButton href="/projects">Projects</LinkButton>} />
      </main>
    );
  }
  return <Studio id={id} />;
}
