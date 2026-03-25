"use client";

import React, { useEffect, useRef } from "react";

import { fr } from "@/lib/strings";

type Props = {
  open: boolean;
  videoLabel: string;
  pending: boolean;
  onDismiss: () => void;
  onConfirm: () => void;
};

/**
 * Accessible confirm dialog for destructive delete (native `<dialog>` + `showModal()`).
 */
export function DeleteVideoConfirmDialog({
  open,
  videoLabel,
  pending,
  onDismiss,
  onConfirm,
}: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open) {
      if (!el.open) el.showModal();
    } else if (el.open) {
      el.close();
    }
  }, [open]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const handleClose = () => {
      onDismiss();
    };
    el.addEventListener("close", handleClose);
    return () => el.removeEventListener("close", handleClose);
  }, [onDismiss]);

  return (
    <dialog
      ref={ref}
      className="open:backdrop:bg-black/75 w-[min(28rem,calc(100%-2rem))] rounded-lg border border-zinc-700 bg-zinc-900 p-6 text-zinc-100 shadow-xl"
      aria-labelledby="delete-video-title"
      aria-describedby="delete-video-desc"
    >
      <h2 id="delete-video-title" className="text-lg font-semibold text-zinc-50">
        {fr.adminDeleteDialogTitle}
      </h2>
      <p id="delete-video-desc" className="mt-2 text-sm text-zinc-300">
        {fr.adminDeleteDialogBody}
      </p>
      <p className="mt-2 text-sm font-medium text-zinc-200">{videoLabel}</p>
      <div className="mt-6 flex justify-end gap-2">
        <button
          type="button"
          className="rounded-md border border-zinc-600 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500"
          onClick={() => ref.current?.close()}
          disabled={pending}
        >
          {fr.adminDeleteCancel}
        </button>
        <button
          type="button"
          className="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400 disabled:opacity-50"
          onClick={onConfirm}
          disabled={pending}
          aria-busy={pending}
        >
          {fr.adminDeleteConfirm}
        </button>
      </div>
    </dialog>
  );
}
