"use client";

import { useEffect, useState } from "react";
import Link from "next/link";


type HealthResponse = {
  status: string;
};


export default function Home() {
  const [backendStatus, setBackendStatus] = useState<string>("checking...");

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const apiBaseUrl =
          process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

        const response = await fetch(`${apiBaseUrl}/health`);

        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }

        const data: HealthResponse = await response.json();

        setBackendStatus(data.status);
      } catch (error) {
        console.error("Failed to connect to backend:", error);
        setBackendStatus("unavailable");
      }
    };

    checkBackend();
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold">TripSync</h1>

        <p className="mt-4 text-lg">
          Backend status:{" "}
          <span className="font-semibold">{backendStatus}</span>
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link href="/trips" className="rounded-xl bg-teal-700 px-5 py-3 font-semibold text-white hover:bg-teal-800">
            我的旅程
          </Link>
          <Link href="/login" className="rounded-xl border border-zinc-300 px-5 py-3 font-semibold hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900">
            登入
          </Link>
          <Link href="/account" className="rounded-xl border border-zinc-300 px-5 py-3 font-semibold hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900">
            我的帳號
          </Link>
        </div>
      </div>
    </main>
  );
}
