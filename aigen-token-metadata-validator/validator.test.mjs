import assert from "node:assert/strict";
import { validateTokenRecords } from "./validator.mjs";

const good = [
  {
    asset_id: "usdc",
    chain: "base",
    address: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    name: "USD Coin",
    symbol: "USDC",
    decimals: 6,
  },
  {
    asset_id: "usdc",
    chain: "ethereum",
    address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    name: "USD Coin",
    symbol: "USDC",
    decimals: 6,
  },
];

const cleanReport = validateTokenRecords(good);
assert.equal(cleanReport.ok, true);
assert.equal(cleanReport.verdict, "PASS");
assert.equal(cleanReport.findings.length, 0);

const spoofed = validateTokenRecords([
  {
    chain: "base",
    address: "0x0000000000000000000000000000000000000001",
    name: "USD\u202ECoin",
    symbol: "USD\u200BC",
    decimals: 6,
  },
]);
assert.equal(spoofed.ok, false);
assert.equal(spoofed.verdict, "BLOCK");
assert(spoofed.findings.some((finding) => finding.code === "name_bidi_override"));
assert(spoofed.findings.some((finding) => finding.code === "symbol_zero_width"));

const mismatched = validateTokenRecords([
  {
    asset_id: "wrapped-thing",
    chain: "base",
    address: "0x0000000000000000000000000000000000000002",
    name: "Wrapped Thing",
    symbol: "WTH",
    decimals: 18,
  },
  {
    asset_id: "wrapped-thing",
    chain: "optimism",
    address: "0x0000000000000000000000000000000000000003",
    name: "Wrapped Thing",
    symbol: "WTH",
    decimals: 6,
  },
]);
assert.equal(mismatched.ok, false);
assert(mismatched.findings.some((finding) => finding.code === "cross_chain_decimals_mismatch"));

const badDecimals = validateTokenRecords([
  {
    chain: "base",
    address: "0x0000000000000000000000000000000000000004",
    name: "Bad Decimals",
    symbol: "BAD",
    decimals: 999,
  },
]);
assert.equal(badDecimals.verdict, "REVIEW");
assert(badDecimals.findings.some((finding) => finding.code === "decimals_invalid"));

console.log("All validator tests passed");
