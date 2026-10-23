"use client";

import { useActionState, useRef } from "react";
import type { DeleteTripState } from "@/lib/trip-types";

export default function DeleteTripForm({
  deleteAction,
  name,
}: {
  deleteAction: () => Promise<DeleteTripState>;
  name: string;
}) {
  const disclosure = useRef<HTMLDetailsElement>(null);
  const [state, action, pending] = useActionState<DeleteTripState, FormData>(
    deleteAction,
    {},
  );

  return (
    <details ref={disclosure} className="max-w-full open:w-full">
      <summary className="cursor-pointer rounded-xl border border-red-200 px-4 py-3 text-sm font-medium text-red-700 hover:bg-red-50 dark:border-red-900 dark:text-red-300 dark:hover:bg-red-950/40">
        刪除旅程
      </summary>
      <form
        action={action}
        className="mt-3 rounded-xl border border-red-200 p-4 dark:border-red-900"
      >
        <p className="text-sm">
          確定刪除「{name}」？每日活動、邀請與成員關聯將一併刪除，無法復原。
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            disabled={pending}
            className="rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {pending ? "刪除中…" : "確認刪除"}
          </button>
          <button
            type="button"
            disabled={pending}
            onClick={() => {
              if (disclosure.current) disclosure.current.open = false;
            }}
            className="rounded-lg border border-zinc-300 px-4 py-2 text-sm dark:border-zinc-700"
          >
            取消
          </button>
        </div>
        <div aria-live="polite">
          {state.error && (
            <p
              role="alert"
              className="mt-3 text-sm text-red-700 dark:text-red-300"
            >
              {state.error}
            </p>
          )}
        </div>
      </form>
    </details>
  );
}
