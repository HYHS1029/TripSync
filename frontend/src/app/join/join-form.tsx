"use client";

import { useActionState, useEffect, useRef } from "react";
import { joinTrip } from "./actions";

export default function JoinForm({ signedIn }: { signedIn: boolean }) {
  const [state, action, pending] = useActionState(joinTrip, {});
  const tokenInput = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const token = window.location.hash.slice(1);
    if (token && tokenInput.current) {
      tokenInput.current.value = token;
      window.history.replaceState(
        window.history.state,
        "",
        window.location.pathname + window.location.search,
      );
    }
  }, []);
  return (
    <form action={action} className="mt-7 space-y-5">
      <input ref={tokenInput} type="hidden" name="token" />
      {state.error && (
        <p
          role="alert"
          className="rounded-xl bg-red-50 p-4 text-sm leading-6 text-red-700 dark:bg-red-950/50 dark:text-red-300"
        >
          {state.error}
        </p>
      )}
      <button
        disabled={pending}
        className="w-full rounded-xl bg-teal-700 px-6 py-3 font-semibold text-white disabled:opacity-50"
      >
        {pending ? "處理中…" : signedIn ? "確認加入旅程" : "登入後繼續"}
      </button>
      <noscript>
        <p className="text-sm text-red-700">
          為保護邀請連結，加入流程需要啟用 JavaScript。
        </p>
      </noscript>
    </form>
  );
}
