import Link from "next/link";

import { PrimaryReadyVideos } from "@/components/home/PrimaryReadyVideos";
import { fr } from "@/lib/strings";

export const dynamic = "force-dynamic";

export default async function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-6 py-16">
      <div className="flex items-start justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">{fr.appTitle}</h1>
        <Link
          href="/admin"
          className="shrink-0 text-sm text-zinc-500 underline-offset-4 hover:text-zinc-300 hover:underline"
        >
          {fr.homeLinkAdmin}
        </Link>
      </div>
      <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6">
        <PrimaryReadyVideos />
      </section>
    </main>
  );
}
