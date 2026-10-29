"use client";

import { useActionState } from "react";
import { requestEmailVerification } from "./actions";

export default function EmailVerificationForm({
  email, pendingEmail,
}: { email: string | null; pendingEmail: string | null }) {
  const [state, action, pending] = useActionState(requestEmailVerification, {});
  const inputStyle = "mt-2 w-full rounded-xl border border-zinc-300 bg-transparent px-4 py-3 dark:border-zinc-700";
  return (
    <section className="mt-8 rounded-2xl border border-zinc-200 bg-white p-6 sm:p-8 dark:border-zinc-800 dark:bg-zinc-900" aria-labelledby="verify-email-heading">
      <h2 id="verify-email-heading" className="text-lg font-semibold">{email ? "更換電子郵件" : "綁定並驗證電子郵件"}</h2>
      <p className="mt-3 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
        驗證後可使用信箱登入。{email ? "新信箱驗證完成前，原信箱仍可使用。" : "目前仍可使用使用者名稱登入；尚未設定恢復方式時，忘記密碼可能無法找回帳號。"}
      </p>
      {pendingEmail && <p className="mt-3 break-all text-sm text-amber-700 dark:text-amber-300">待驗證：{pendingEmail}。若連結已過期，可重新寄送。</p>}
      <form action={action} className="mt-6 space-y-5">
        <div>
          <label htmlFor="verification-email" className="text-sm font-medium">電子郵件</label>
          <input id="verification-email" name="email" type="email" autoComplete="email" required maxLength={254} defaultValue={state.email ?? pendingEmail ?? email ?? ""} className={inputStyle} />
        </div>
        <div>
          <label htmlFor="verification-password" className="text-sm font-medium">目前密碼</label>
          <input id="verification-password" name="password" type="password" autoComplete="current-password" required minLength={8} maxLength={128} className={inputStyle} />
        </div>
        <div aria-live="polite">
          {state.error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{state.error}</p>}
          {state.message && <p role="status" className="text-sm text-teal-700 dark:text-teal-300">{state.message}</p>}
        </div>
        <button disabled={pending} className="rounded-xl bg-teal-700 px-5 py-3 font-semibold text-white disabled:opacity-50">{pending ? "寄送中…" : "寄送驗證信"}</button>
      </form>
    </section>
  );
}
