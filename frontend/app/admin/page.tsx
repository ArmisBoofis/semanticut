import Link from "next/link";

import { AdminVideoList } from "@/components/admin/AdminVideoList";
import { fr } from "@/lib/strings";

export default function AdminPage() {
  return (
    <main className="mx-auto min-h-screen max-w-5xl px-6 py-16">
      <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
            {fr.adminTitle}
          </h1>
          <p className="mt-1 text-sm text-zinc-500">{fr.adminSubtitle}</p>
        </div>
        <Link
          href="/"
          className="text-sm text-zinc-400 underline-offset-4 hover:text-zinc-200 hover:underline"
        >
          {fr.adminBackHome}
        </Link>
      </header>
      <AdminVideoList />
    </main>
  );
}
