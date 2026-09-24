"use client";

import { useEffect, useState } from "react";


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
      </div>
    </main>
  );
}