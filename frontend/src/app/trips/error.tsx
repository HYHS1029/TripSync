"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

export default function TripsError({ reset }: { reset: () => void }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <section className="py-16 text-center">
      <h1 className="text-2xl font-bold">暫時無法載入旅程</h1>
      <p className="mb-6 mt-3 text-zinc-600 dark:text-zinc-400">
        請稍後重試，你的旅程資料仍保留在帳號中。
      </p>
      <button
        disabled={pending}
        onClick={() =>
          startTransition(() => {
            router.refresh();
            reset();
          })
        }
        className="rounded-xl bg-teal-700 px-5 py-3 font-semibold text-white disabled:opacity-60"
      >
        {pending ? "重試中…" : "重試"}
      </button>
    </section>
  );
}
