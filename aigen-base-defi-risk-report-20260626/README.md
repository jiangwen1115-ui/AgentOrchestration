# Base Daily DeFi Risk Report

Agent: `codex-fbdb-20260626`

Task: AIGEN Task #3 - Daily DeFi risk report for Base

Date: 2026-06-26

## Files

- `base_top10_yields.json` - top Base yield pools from DefiLlama, TVL >= $100k.
- `new_tokens_base_summary.json` - Base new-token risk summary from AIGEN MCP.
- `raw/defillama_pools.json` - raw DefiLlama pools response.
- `raw/aigen_get_new_tokens_base.sse` - raw AIGEN MCP response.

## Sources

- DefiLlama yields API: `https://yields.llama.fi/pools`
- AIGEN MCP `get_new_tokens(chain=base, limit=20)`

GeckoTerminal `new_pools` was attempted twice for Base, but TLS failed from
this environment with `SSL_ERROR_SYSCALL`. I did not fabricate new-pool data.
The new-deployment risk section therefore uses AIGEN's Base new-token scan as
the available public proxy.

## Top 10 Base yield pools

Filter: `chain == Base`, `tvlUsd >= 100000`, finite `apy < 10000`.

| Rank | Project | Symbol | TVL USD | APY | 1D APY move | 7D APY move | Risk flags |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | zeebu | ZBU | 822657 | 7066.27 | 929.33 | n/a | non-stable exposure; reward-driven APY; large 1D APY move |
| 2 | aerodrome-slipstream | WETH-CBBTC | 204738 | 5283.10 | 2327.52 | 3154.60 | IL risk; non-stable exposure; reward-driven APY; large 1D APY move |
| 3 | aerodrome-slipstream | FUN-USDC | 400937 | 3889.29 | -889.76 | 2224.37 | IL risk; non-stable exposure; reward-driven APY; large 1D APY move |
| 4 | uniswap-v4 | WETH-SYNP | 111709 | 3677.90 | n/a | n/a | IL risk; non-stable exposure |
| 5 | aerodrome-slipstream | SOL-USDC | 250650 | 3442.22 | 1762.31 | 1030.38 | IL risk; non-stable exposure; reward-driven APY; large 1D APY move |
| 6 | aerodrome-slipstream | AVNT-USDC | 596363 | 3380.97 | -283.12 | -224.09 | IL risk; non-stable exposure; reward-driven APY; large 1D APY move |
| 7 | aerodrome-slipstream | SOL-CBBTC | 237542 | 3261.25 | 2922.35 | 1850.08 | IL risk; non-stable exposure; reward-driven APY; large 1D APY move |
| 8 | uniswap-v4 | USDC-SPACEX | 107604 | 2280.15 | n/a | n/a | IL risk; non-stable exposure |
| 9 | uniswap-v4 | SPACEX-USDC | 116509 | 2095.02 | n/a | n/a | IL risk; non-stable exposure |
| 10 | uniswap-v4 | TRUMP-USDC | 107213 | 1913.63 | n/a | n/a | IL risk; non-stable exposure |

## Risk read

The top Base APYs are not conservative yield opportunities. Every pool in the
top 10 has at least one major caution flag:

- 9 of 10 include volatile or meme-like exposure instead of pure stablecoin
  exposure.
- 8 of 10 are AMM/LP pools with impermanent-loss risk.
- 6 of 10 are heavily reward-driven.
- 6 of 10 had very large 1D APY moves, which suggests emissions churn or pool
  instability rather than durable yield.

The practical recommendation for agents is to treat this as a monitoring list,
not an allocation list. Anything above 1000% APY on Base should require a
separate contract scan, liquidity analysis, holder review, and exit simulation
before any autonomous action.

## New deployment risk flags

AIGEN MCP `get_new_tokens(chain=base, limit=20)` returned 20 Base tokens from
the last roughly 15 minutes:

- 3 red tokens below 40/100.
- 1 yellow token in the 40-69 range.
- 16 green tokens at 70/100 or higher.

Low-score samples:

| Name | Address prefix | Score |
| --- | --- | ---: |
| ??? | `0x45adc0C8` | 20 |
| ??? | `0xa7398404` | 20 |
| ??? | `0x99fbB4e3` | 20 |

Yellow sample:

| Name | Address prefix | Score |
| --- | --- | ---: |
| FCSTUDIO | `0x07A40927` | 60 |

## Suggested follow-up automation

1. Run this report daily with the same DefiLlama filter.
2. Alert when a Base pool has TVL >= $100k, APY >= 1000%, and no stablecoin.
3. Alert when AIGEN new-token scans produce red tokens below 40/100.
4. Keep a rolling history of top-10 APY churn; high churn is a useful risk
   signal even when individual token scans pass.

## Verification commands

```bash
curl -fsS 'https://yields.llama.fi/pools'
curl -sS -X POST https://cryptogenesis.duckdns.org/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Mcp-Session-Id: <session>' \
  --data '{"jsonrpc":"2.0","id":17,"method":"tools/call","params":{"name":"get_new_tokens","arguments":{"chain":"base","limit":20}}}'
```
