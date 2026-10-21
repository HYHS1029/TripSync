"use client";

import { useActionState } from "react";
import { login } from "./actions";

export default function LoginForm() {
  const [state, formAction, pending] = useActionState(login, {});

  return (
    <form action={formAction} className="space-y-5">
      <div>
        <label htmlFor="email" className="mb-2 block text-sm font-medium">
          電子郵件
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          defaultValue={state.email}
          required
          maxLength={254}
          placeholder="you@example.com"
          className="w-full rounded-xl border border-zinc-300 bg-transparent px-4 py-3 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20 dark:border-zinc-700"
          aria-describedby={state.error ? "login-error" : undefined}
        />
      </div>
      <div>
        <label htmlFor="password" className="mb-2 block text-sm font-medium">
          密碼
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          minLength={8}
          maxLength={128}
          className="w-full rounded-xl border border-zinc-300 bg-transparent px-4 py-3 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20 dark:border-zinc-700"
          aria-describedby={state.error ? "login-error" : undefined}
        />
      </div>
      <div aria-live="polite" aria-atomic="true">
        {state.error && (
          <p
            id="login-error"
            role="alert"
            className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300"
          >
            {state.error}
          </p>
        )}
      </div>
      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-xl bg-teal-700 px-4 py-3 font-semibold text-white transition-colors hover:bg-teal-800 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-600 disabled:cursor-wait disabled:opacity-60"
      >
        {pending ? "登入中…" : "登入"}
      </button>
    </form>
  );
}
