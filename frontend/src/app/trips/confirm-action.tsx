"use client";
import { useActionState } from "react";
import type { MutationState } from "@/lib/trip-types";

export default function ConfirmAction({
  action,
  label,
  confirmation,
}: {
  action: (state: MutationState) => Promise<MutationState>;
  label: string;
  confirmation: string;
}) {
  const [state, formAction, pending] = useActionState(action, {});
  return (
    <details className="text-sm">
      <summary className="cursor-pointer rounded-lg px-3 py-2 text-red-700 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-950/40">
        {label}
      </summary>
      <form
        action={formAction}
        className="mt-2 max-w-sm space-y-3 rounded-xl border border-red-200 p-4 dark:border-red-900"
      >
        <p className="leading-6 text-zinc-600 dark:text-zinc-300">
          {confirmation}
        </p>
        <div aria-live="polite">
          {state.error && (
            <p role="alert" className="text-red-700 dark:text-red-300">
              {state.error}
            </p>
          )}
          {state.success && (
            <p role="status" className="text-teal-700 dark:text-teal-300">
              {state.success}
            </p>
          )}
        </div>
        <button
          disabled={pending}
          className="rounded-lg bg-red-700 px-4 py-2 font-medium text-white disabled:opacity-50"
        >
          {pending ? "處理中…" : `確認${label}`}
        </button>
        <p className="text-xs text-zinc-500">
          不執行時，可再次點選「{label}」收起。
        </p>
      </form>
    </details>
  );
}
