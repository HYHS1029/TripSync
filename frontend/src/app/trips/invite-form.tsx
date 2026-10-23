"use client";
import { useActionState, useRef, useState } from "react";
import type { InvitationState } from "@/lib/trip-types";

export default function InviteForm({
  createAction,
}: {
  createAction: () => Promise<InvitationState>;
}) {
  const [state, action, pending] = useActionState<InvitationState, FormData>(
    createAction,
    {},
  );
  const [copy, setCopy] = useState<{
    path: string;
    url: string;
    message: string;
  } | null>(null);
  const input = useRef<HTMLInputElement>(null);
  async function copyLink() {
    if (!state.invitePath) return;
    const url = new URL(state.invitePath, window.location.origin).href;
    try {
      await navigator.clipboard.writeText(url);
      setCopy({ path: state.invitePath, url, message: "邀請連結已複製。" });
    } catch {
      setCopy({
        path: state.invitePath,
        url,
        message: "請選取下方完整連結，手動複製。",
      });
      if (input.current) {
        input.current.value = url;
        input.current.select();
      }
    }
  }
  return (
    <div className="space-y-4">
      <form action={action}>
        <button
          disabled={pending}
          className="rounded-xl bg-teal-700 px-5 py-3 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
        >
          {pending ? "建立中…" : "建立邀請連結"}
        </button>
      </form>
      {state.error && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {state.error}
        </p>
      )}
      {state.invitePath && (
        <div className="space-y-3 rounded-xl bg-teal-50 p-4 dark:bg-teal-950/50">
          <p className="text-sm font-medium">
            邀請已建立，請複製並私下分享給一位旅伴。
          </p>
          <label
            htmlFor="invitation-link"
            className="block text-xs text-zinc-600 dark:text-zinc-400"
          >
            邀請連結（離開此頁後不再顯示）
          </label>
          <input
            ref={input}
            id="invitation-link"
            readOnly
            value={
              copy?.path === state.invitePath ? copy.url : state.invitePath
            }
            onFocus={(event) => event.target.select()}
            className="w-full rounded-lg border border-teal-200 bg-white px-3 py-2 text-sm dark:border-teal-900 dark:bg-zinc-900"
          />
          <button
            type="button"
            onClick={copyLink}
            className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white"
          >
            複製完整連結
          </button>
          <p role="status" className="text-xs text-teal-800 dark:text-teal-200">
            {copy?.path === state.invitePath
              ? copy.message
              : "有效期限為七天，成功加入一位新成員後即失效。"}
          </p>
        </div>
      )}
    </div>
  );
}
