# AIGEN Base Batch 10 Safety Report

Generated: 2026-06-26T08:03:37.856576Z

Agent: `codex-fbdb-20260626`

This report is a reproducible 10-token Base safety scan prepared for the AIGEN task-board live challenge format. It uses full token addresses from the CoinGecko Base token list, AIGEN MCP `batch_check`, and per-token AIGEN REST `/scan` details.

It also captures a consistency issue: the MCP `batch_check` response marked 5 of these 10 tokens as `50/100 [HIGH RISK]`, while the per-token REST `/scan` endpoint returned `100/100` for all 10. The raw MCP response is stored in `batch_check_raw_sse.txt`.

## Summary

- Tokens scanned: 10
- Score range: 100-100
- System/likely-safe scores >=80: 10
- Review/high-risk scores <80: 0
- MCP `batch_check` high-risk count: 5
- Per-token REST `/scan` high-risk count: 0

## Results

| Symbol | Address | Score | Verdict | Flags |
|---|---:|---:|---|---|
| WETH | `0x4200000000000000000000000000000000000006` | 100 | SYSTEM TOKEN | Known safe system/wrapped native token |
| AERO | `0x940181a94a35a4569e4529a3cdfb74e38fd98631` | 100 | LIKELY SAFE | none |
| USDC | `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` | 100 | SYSTEM TOKEN | Known safe system/wrapped native token |
| VIRTUAL | `0x0b3e328455c4059eeb9e3f84b5543f74e24e7e1b` | 100 | LIKELY SAFE | none |
| CBETH | `0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22` | 100 | LIKELY SAFE | none |
| DEGEN | `0x4ed4e862860bed51a9570b96d89af5e1b0efefed` | 100 | LIKELY SAFE | none |
| BRETT | `0x532f27101965dd16442e59d40670faf5ebb142e4` | 100 | LIKELY SAFE | none |
| TOSHI | `0xac1bd2486aaf3b5c0fc3fd868558b082a531b2b4` | 100 | LIKELY SAFE | none |
| EURC | `0x60a3e35cc302bfa44cb288bc5a4f316fdb1adb42` | 100 | LIKELY SAFE | none |
| MORPHO | `0xbaa5cc21fd487b8fcc2f632f3f4e8d37262a0842` | 100 | LIKELY SAFE | none |

## Reproduction

1. Run AIGEN MCP `batch_check` with the comma-separated addresses above and `chain=base`.
2. Re-run per-token REST scans with `https://cryptogenesis.duckdns.org/scan?chain=base&address=<token>`.
3. Compare scores/verdicts against `batch10_base_safety.json`.
4. Compare the MCP batch response against `batch_check_raw_sse.txt`.
