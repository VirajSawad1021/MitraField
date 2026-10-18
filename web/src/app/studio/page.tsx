"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { Studio } from "@/components/studio/Studio";

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
  const router = useRouter();
  useEffect(() => { if (!id) router.replace("/projects"); }, [id, router]);   // the studio always opens a project
  return id ? <Studio id={id} /> : null;
}
