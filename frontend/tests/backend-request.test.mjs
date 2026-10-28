import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module, { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const filename = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/lib/backend-request.ts");
const loaded = new Module(filename);
const nativeRequire = createRequire(filename);
loaded.require = (name) => name === "server-only" ? {} : nativeRequire(name);
loaded._compile(ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText, filename);
const { backendRequest, API_BASE_URL } = loaded.exports;

function protectionToken(t, value) {
  const original = process.env.API_PROTECTION_BYPASS;
  process.env.API_PROTECTION_BYPASS = value;
  t.after(() => {
    if (original === undefined) delete process.env.API_PROTECTION_BYPASS;
    else process.env.API_PROTECTION_BYPASS = original;
  });
}

test("protected API requests keep bearer auth and send only a server-side bypass header", async (t) => {
  protectionToken(t, "test-only-protection-token");
  let request;
  t.mock.method(globalThis, "fetch", async (url, init) => {
    request = { url, init };
    return new Response("{}", { status: 200 });
  });
  await backendRequest("/trips", { headers: { Authorization: "Bearer test-jwt" }, cache: "force-cache", redirect: "follow" });
  assert.equal(request.url, `${API_BASE_URL}/trips`);
  assert.equal(request.init.headers.get("Authorization"), "Bearer test-jwt");
  assert.equal(request.init.headers.get("x-vercel-protection-bypass"), "test-only-protection-token");
  assert.equal(request.init.cache, "no-store");
  assert.equal(request.init.redirect, "error");
  assert.ok(request.init.signal instanceof AbortSignal);
});

test("normal API requests work without a platform-specific protection token", async (t) => {
  protectionToken(t, "");
  t.mock.method(globalThis, "fetch", async (_url, init) => {
    assert.equal(init.headers.has("x-vercel-protection-bypass"), false);
    return new Response("{}", { status: 200 });
  });
  assert.equal((await backendRequest("/health")).status, 200);
});

test("invalid API paths are rejected before credentials can be sent", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => new Response("{}"));
  for (const value of ["https://example.com", "//example.com", "/\\example.com"]) {
    await assert.rejects(() => backendRequest(value), /Invalid API path/);
  }
  assert.equal(fetch.mock.callCount(), 0);
});
