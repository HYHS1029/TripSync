import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const testDirectory = path.dirname(fileURLToPath(import.meta.url));

function loadTypeScript(relativePath) {
  const filename = path.resolve(testDirectory, relativePath);
  const source = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  }).outputText;
  const loaded = new Module(filename);
  loaded.filename = filename;
  loaded._compile(source, filename);
  return loaded.exports;
}
const { parseMinor, amountInput, money } = loadTypeScript(
  "../src/lib/money.ts",
);
const { decodePolyline } = loadTypeScript("../src/lib/maps-browser.ts");

test("decimal input preserves minor units without floating-point arithmetic", () => {
  assert.equal(parseMinor("100.01", 2), 10001);
  assert.equal(parseMinor("0.29", 2), 29);
  assert.equal(parseMinor("1.2", 2), 120);
  assert.equal(parseMinor("1001", 0), 1001);
  assert.equal(parseMinor("10000000000.00", 2), 1000000000000);
});
test("invalid precision, negative values, exponents and excessive amounts are rejected", () => {
  for (const value of [
    "",
    "-1",
    "NaN",
    "Infinity",
    "1e2",
    "100.001",
    "1,000",
    "10000000000.01",
  ]) {
    assert.equal(parseMinor(value, 2), null, value);
  }
  assert.equal(parseMinor("1.1", 0), null);
});
test("minor-unit strings round trip for both decimal and zero-decimal currencies", () => {
  for (const digits of [0, 2])
    for (const minor of [0, 1, 29, 10001, 1000000000000]) {
      assert.equal(parseMinor(amountInput(minor, digits), digits), minor);
    }
  assert.match(money(1001, "JPY", 0), /1,001/);
});
test("Google encoded polylines decode into the documented coordinates", () => {
  assert.deepEqual(decodePolyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@"), [
    { lat: 38.5, lng: -120.2 },
    { lat: 40.7, lng: -120.95 },
    { lat: 43.252, lng: -126.453 },
  ]);
  assert.deepEqual(decodePolyline(""), []);
  assert.throws(() => decodePolyline("_p~iF"), /Invalid/);
});
