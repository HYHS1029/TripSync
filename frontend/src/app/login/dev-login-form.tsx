"use client";

import { useActionState } from "react";
import { developmentLogin } from "./actions";

export default function DevelopmentLoginForm({ returnToJoin = false }: { returnToJoin?: boolean }) {
  const [state, action, pending] = useActionState(developmentLogin, {});

  return (
    <form action={action} className="mt-6 border-t border-zinc-200 pt-6 dark:border-zinc-700">
      {returnToJoin && <input type="hidden" name="next" value="join" />}
      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-xl border border-teal-600 bg-teal-50 px-4 py-3 font-semibold text-teal-800 hover:bg-teal-100 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-600 disabled:cursor-wait disabled:opacity-60 dark:bg-teal-950 dark:text-teal-200 dark:hover:bg-teal-900"
      >
        {pending ? "登入中…" : "開發者快速登入"}
      </button>
      <p className="mt-2 text-center text-xs leading-5 text-zinc-500 dark:text-zinc-400">
        本機測試專用・旅程與記帳資料會保留
      </p>
      <div aria-live="polite" aria-atomic="true">
        {state.error && <p role="alert" className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">{state.error}</p>}
      </div>
    </form>
  );
}
