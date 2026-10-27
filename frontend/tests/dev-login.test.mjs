import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const filename = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/lib/dev-login-policy.ts");
const loaded = new Module(filename);
loaded._compile(ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText, filename);
const { allowsDevelopmentLogin } = loaded.exports;
const settings = { nodeEnv: "development", enabled: "true", apiBaseUrl: "http://127.0.0.1:8000" };
const localHeaders = { host: "localhost:3000", "x-forwarded-host": "localhost:3000", "x-forwarded-for": "127.0.0.1" };

test("local development GET and same-origin POST can use the configured account", () => {
  assert.equal(allowsDevelopmentLogin(settings, new Headers(localHeaders)), true);
  assert.equal(allowsDevelopmentLogin(settings, new Headers({ ...localHeaders, origin: "http://localhost:3000" }), true), true);
});

test("production and unconfigured environments always disable the shortcut", () => {
  for (const nodeEnv of ["production", "test", undefined]) {
    assert.equal(allowsDevelopmentLogin({ ...settings, nodeEnv }, new Headers(localHeaders)), false);
  }
  for (const enabled of [undefined, "false", "1"]) {
    assert.equal(allowsDevelopmentLogin({ ...settings, enabled }, new Headers(localHeaders)), false);
  }
});

test("remote, proxied, malformed or cross-origin requests cannot use the shortcut", () => {
  for (const headers of [
    { ...localHeaders, host: "example.com" },
    { ...localHeaders, host: "localhost.example.com:3000" },
    { ...localHeaders, host: "localhost:3000/path" },
    { ...localHeaders, host: "example.com@localhost:3000" },
    { ...localHeaders, "x-forwarded-for": "192.168.1.20" },
    { ...localHeaders, "x-forwarded-for": "127.0.0.1, 192.168.1.20" },
    { ...localHeaders, "x-forwarded-host": "example.com" },
    { ...localHeaders, "x-real-ip": "192.168.1.20" },
    { ...localHeaders, forwarded: "for=192.168.1.20" },
    { ...localHeaders, origin: "http://example.com" },
    { ...localHeaders, origin: "null" },
    { host: "localhost:3000" },
  ]) {
    assert.equal(allowsDevelopmentLogin(settings, new Headers(headers)), false, JSON.stringify(headers));
  }
  assert.equal(allowsDevelopmentLogin(settings, new Headers(localHeaders), true), false);
});

test("only a local HTTP API is allowed", () => {
  for (const apiBaseUrl of ["https://api.example.com", "http://localhost.example.com:8000", "http://user:password@localhost:8000", "http://localhost:8000/path"]) {
    assert.equal(allowsDevelopmentLogin({ ...settings, apiBaseUrl }, new Headers(localHeaders)), false);
  }
});
