import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src");
function load(relative, imports = {}) {
  const filename = path.join(root, relative);
  const loaded = new Module(filename);
  loaded.require = (name) => {
    if (name === "server-only") return {};
    if (Object.hasOwn(imports, name)) return imports[name];
    throw new Error(`Unexpected dependency: ${name}`);
  };
  loaded._compile(ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText, filename);
  return loaded.exports;
}

const features = load("lib/auth-features.ts");
function disableFeature(t) {
  const original = process.env.EMAIL_VERIFICATION_ENABLED;
  delete process.env.EMAIL_VERIFICATION_ENABLED;
  t.after(() => {
    if (original === undefined) delete process.env.EMAIL_VERIFICATION_ENABLED;
    else process.env.EMAIL_VERIFICATION_ENABLED = original;
  });
}

test("email verification stays disabled until explicitly enabled", (t) => {
  disableFeature(t);
  assert.equal(features.isEmailVerificationEnabled(), false);
  process.env.EMAIL_VERIFICATION_ENABLED = "false";
  assert.equal(features.isEmailVerificationEnabled(), false);
  process.env.EMAIL_VERIFICATION_ENABLED = "true";
  assert.equal(features.isEmailVerificationEnabled(), true);
});

test("disabled verification actions reject direct calls before reading credentials or making requests", async (t) => {
  disableFeature(t);
  const forbidden = () => { throw new Error("Disabled actions must not perform side effects"); };
  const imports = {
    "@/lib/auth-features": features,
    "@/lib/auth": { SESSION_COOKIE: "test-session" },
    "@/lib/backend-request": { backendRequest: forbidden },
    "@/lib/email-verification": { isEmailVerificationToken: forbidden },
    "next/headers": { cookies: forbidden },
    "next/cache": { revalidatePath: forbidden },
    "next/navigation": { redirect: forbidden },
  };
  const { requestEmailVerification } = load("app/account/actions.ts", imports);
  const { confirmEmailVerification } = load("app/verify-email/actions.ts", imports);
  const form = new FormData();
  form.set("email", "test@example.com");
  form.set("password", "test-only-password");
  form.set("token", "x".repeat(43));
  assert.deepEqual(await requestEmailVerification({}, form), { error: "目前尚未開放信箱驗證。" });
  assert.deepEqual(await confirmEmailVerification({}, form), { error: "目前尚未開放信箱驗證。" });
});
