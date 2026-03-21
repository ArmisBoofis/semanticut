import { fetchBackendHealth } from "@/lib/fetchBackendHealth";
import { fr } from "@/lib/strings";

export const dynamic = "force-dynamic";

export default async function Home() {
  const health = await fetchBackendHealth();

  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center gap-6 px-6 py-16">
      <h1 className="text-2xl font-semibold tracking-tight">{fr.appTitle}</h1>
      <section
        className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6"
        aria-live="polite"
      >
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-zinc-400">
          {fr.pageHeading}
        </h2>
        <p className="text-base leading-relaxed">
          {health.ok ? fr.backendOk : fr.backendUnavailable}
        </p>
      </section>
    </main>
  );
}
