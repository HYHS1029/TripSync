"use client";

import { useActionState } from "react";
import { register, type RegisterState } from "./actions";

type Field = {
  name: "email" | "username" | "password" | "confirm_password";
  label: string;
  type: "email" | "text" | "password";
  autoComplete: string;
  maxLength: number;
  minLength?: number;
  pattern?: string;
  hint?: string;
};

const fields: Field[] = [
  {
    name: "username",
    label: "使用者名稱",
    type: "text",
    autoComplete: "username",
    minLength: 3,
    maxLength: 50,
    pattern: "[A-Za-z0-9_]+",
    hint: "3–50 個英文字母、數字或底線，登入時區分大小寫。",
  },
  {
    name: "password",
    label: "密碼",
    type: "password",
    autoComplete: "new-password",
    minLength: 8,
    maxLength: 128,
    hint: "8–128 個字元。",
  },
  {
    name: "confirm_password",
    label: "確認密碼",
    type: "password",
    autoComplete: "new-password",
    minLength: 8,
    maxLength: 128,
  },
  {
    name: "email",
    label: "電子郵件（選填）",
    type: "email",
    autoComplete: "email",
    maxLength: 254,
    hint: "登入後可寄送驗證信；完成驗證後才能用信箱登入。",
  },
];

const initialState: RegisterState = { values: { email: "", username: "" } };

export default function RegisterForm({
  returnToJoin = false,
  emailVerificationEnabled = false,
}: {
  returnToJoin?: boolean;
  emailVerificationEnabled?: boolean;
}) {
  const [state, formAction, pending] = useActionState(register, initialState);

  return (
    <form action={formAction} className="space-y-5">
      {returnToJoin && <input type="hidden" name="next" value="join" />}
      {fields.map((field) => {
        if (field.name === "email" && !emailVerificationEnabled) return null;
        const error = state.fieldErrors?.[field.name];
        return (
          <div key={field.name}>
            <label
              htmlFor={field.name}
              className="mb-2 block text-sm font-medium"
            >
              {field.label}
            </label>
            <input
              id={field.name}
              name={field.name}
              type={field.type}
              autoComplete={field.autoComplete}
              required={field.name !== "email"}
              minLength={field.minLength}
              maxLength={field.maxLength}
              pattern={field.pattern}
              defaultValue={
                field.name === "email" || field.name === "username"
                  ? state.values[field.name]
                  : undefined
              }
              className="w-full rounded-xl border border-zinc-300 bg-transparent px-4 py-3 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20 dark:border-zinc-700"
              aria-invalid={Boolean(error)}
              aria-describedby={
                error
                  ? `${field.name}-error`
                  : field.hint
                    ? `${field.name}-hint`
                    : undefined
              }
            />
            {field.hint && (
              <p
                id={`${field.name}-hint`}
                className="mt-2 text-xs text-zinc-500 dark:text-zinc-400"
              >
                {field.hint}
              </p>
            )}
            {error && (
              <p
                id={`${field.name}-error`}
                className="mt-2 text-sm text-red-700 dark:text-red-300"
              >
                {error}
              </p>
            )}
          </div>
        );
      })}
      <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-400">
        {emailVerificationEnabled
          ? "建議登入後綁定並驗證信箱。未設定恢復方式時，忘記密碼可能無法找回帳號。"
          : "請記住使用者名稱並妥善保管密碼，目前尚未提供忘記密碼功能。"}
      </p>
      <div aria-live="polite" aria-atomic="true">
        {state.error && (
          <p
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
        {pending ? "建立帳號中…" : "建立帳號"}
      </button>
    </form>
  );
}
