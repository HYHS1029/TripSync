"use client";

import { useActionState, useEffect, useRef } from "react";
import { confirmEmailVerification } from "./actions";

export default function VerifyEmailForm({ signedIn }: { signedIn: boolean }) {
  const [state, action, pending] = useActionState(confirmEmailVerification, {});
  const tokenInput = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const token = window.location.hash.slice(1);
    if (token && tokenInput.current) {
      tokenInput.current.value = token;
      window.history.replaceState(window.history.state, "", window.location.pathname);
    }
  }, []);
  return (
    <form action={action} className="mt-6 space-y-5">
      <input ref={tokenInput} type="hidden" name="token" />
      {state.error && <p role="alert" className="text-sm leading-6 text-red-700 dark:text-red-300">{state.error}</p>}
      <button disabled={pending} className="w-full rounded-xl bg-teal-700 px-5 py-3 font-semibold text-white disabled:opacity-50">{pending ? "處理中…" : signedIn ? "確認驗證信箱" : "登入後繼續驗證"}</button>
      <noscript><p className="text-sm text-red-700">為保護驗證連結，此流程需要啟用 JavaScript。</p></noscript>
    </form>
  );
}
