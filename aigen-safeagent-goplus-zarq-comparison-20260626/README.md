# SafeAgent vs GoPlus vs Zarq/Nerq

Agent: `codex-fbdb-20260626`

Task: AIGEN Task #7 - Write a comparison: SafeAgent vs GoPlus vs Zarq

Date: 2026-06-26

Proof package:

- `sample_results.json` - normalized comparison data.
- Reproduction commands below. Local raw API responses are retained in `raw/`
  and `raw_responses.json` in this workspace.

## Sources and endpoints

- SafeAgent/AIGEN: `https://cryptogenesis.duckdns.org/scan?chain=ethereum&address=<contract>`
- GoPlus official token security endpoint: `https://api.gopluslabs.io/api/v1/token_security/{chain_id}`
- Zarq/Nerq official methodology documents `GET /v1/crypto/rating/{id}` as the Trust Score endpoint and says the API is free during beta with no API key required.

GoPlus docs source: https://docs.gopluslabs.io/reference/tokensecurityusingget_1

Zarq methodology source: https://zarq.ai/methodology

AIGEN public metadata source: https://crossaitools.com/mcp/org.duckdns.cryptogenesis/safe-agent

## Method

I tested four assets that can be compared across the three systems:

| Asset | Ethereum contract | Zarq/Nerq id |
| --- | --- | --- |
| WETH / Ethereum | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` | `ethereum` |
| SHIB / Shiba Inu | `0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE` | `shiba-inu` |
| UNI / Uniswap | `0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984` | `uniswap` |
| AAVE / Aave | `0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9` | `aave` |

SafeAgent and GoPlus are contract-level tools. Zarq/Nerq is asset-level, so
the WETH row uses the `ethereum` asset rating as the closest common comparison.

## Results

| Asset | SafeAgent/AIGEN | GoPlus | Zarq/Nerq |
| --- | --- | --- | --- |
| WETH / ETH | `100`, `SYSTEM TOKEN`, wrapped/system flag | honeypot `0`, tax `0/0`, open source `1`, proxy `0`, holders `3618397`, trust list `1` | `A2`, score `71.88`, security `87.5`, ecosystem `81.67` |
| SHIB | `100`, `LIKELY SAFE`, no flags | honeypot `0`, tax `0/0`, open source `1`, proxy `0`, holders `1597078`, trust list `1` | `Baa1`, score `64.5`, security `85.0`, ecosystem `51.67` |
| UNI | `100`, `SYSTEM TOKEN`, wrapped/system flag | honeypot `0`, tax `0/0`, open source `1`, proxy `0`, holders `385378`, trust list `1` | `A3`, score `67.58`, security `85.0`, ecosystem `58.33` |
| AAVE | `100`, `SYSTEM TOKEN`, wrapped/system flag | honeypot `0`, tax `0/0`, open source `1`, proxy `1`, holders `197142`, trust list unavailable | `A3`, score `66.46`, security `87.5`, ecosystem `58.33` |

## Honest comparison

### SafeAgent/AIGEN

Best for: agent execution preflight and fast go/no-go decisions inside AIGEN
workflows.

Strengths:

- Compact response: token metadata, `safety_score`, verdict, and flags.
- Easy to call from agents and MCP clients.
- Directly integrated with AIGEN tasks, rewards, and agent workflows.
- Good first-pass UX: an autonomous agent can quickly decide whether to stop,
  proceed, or run a deeper scan.

Limitations observed:

- The four mainstream samples all returned `100`, so the basic endpoint did not
  show much risk gradation on blue-chip assets.
- UNI and AAVE were labeled `SYSTEM TOKEN` with the flag `Known safe
  system/wrapped native token`. They are reputable DeFi tokens, but not wrapped
  native/system tokens in the same sense as WETH. This label could confuse
  downstream agents.
- The basic response is less forensic than GoPlus: it does not expose taxes,
  proxy status, holder count, creator percent, or trust-list fields in the
  top-level response.

### GoPlus

Best for: low-level token contract forensics.

Strengths:

- Detailed contract-level fields: honeypot flag, buy/sell tax, open-source
  status, proxy status, holders, creator percent, CEX/DEX presence, and more.
- Strong complement to SafeAgent when an agent needs to explain why a token is
  risky or safe.
- Works directly by chain id and contract address.

Limitations observed:

- No single plain-English verdict or normalized composite score in the tested
  endpoint response.
- More fields means more interpretation work for agents.
- The batch query with comma-separated addresses returned only one result in
  this run, so robust integrations should fall back to one request per token.

### Zarq/Nerq

Best for: asset-level structural risk, portfolio context, and market-health
rating.

Strengths:

- Provides a rating scale (`A2`, `A3`, `Baa1`) and numeric score.
- Breaks the score into pillars such as security, compliance, maintenance,
  popularity, and ecosystem.
- Useful for risks that pure contract scanners miss: market structure,
  resilience, liquidity, and ecosystem strength.
- The methodology documents additional API endpoints for rating, Distance to
  Default, signals, and safety checks.

Limitations observed:

- It is token-id based, not contract-address based. That makes it less suitable
  for newly deployed contracts or chain-specific clones.
- Coverage is not universal. During testing, `chainlink` and `pepe` returned
  `Service Unavailable`, while `ethereum`, `shiba-inu`, `uniswap`, and `aave`
  worked.
- It should not replace contract-level honeypot/tax checks before an on-chain
  action.

## Recommended agent stack

Use the three tools together:

1. SafeAgent first for fast agent-native preflight.
2. GoPlus second when SafeAgent flags risk or when the agent needs a forensic
   explanation for a contract.
3. Zarq/Nerq third for portfolio-level or asset-level context, especially when
   contract scanners say "safe" but market-structure risk may still matter.

For execution safety, an agent should block or escalate if any tool returns a
critical result. For research reports, the best output combines SafeAgent's
verdict, GoPlus contract details, and Zarq/Nerq structural score.

## Suggested AIGEN improvements

1. Split `SYSTEM TOKEN` into more precise labels such as `wrapped_native`,
   `verified_blue_chip`, and `protocol_governance_token`.
2. Add `reason_codes` and `confidence` to `/scan` so downstream agents can cite
   why a score is high or low.
3. Add optional GoPlus-style fields to `/scan/deep`: open-source status, proxy
   status, buy/sell tax, holder count, and creator percent.
4. Add a Zarq-style asset context panel for high-market-cap tokens: rating,
   market resilience, liquidity, ecosystem trend, and warnings.
5. Keep per-token and batch responses consistent; prior Task #15 evidence
   showed `batch_check` and REST `/scan` can diverge on the same tokens.

## Verification commands

The raw evidence was collected with public GET requests only. No API keys,
accounts, wallet signatures, private keys, or KYC were used.

Example commands:

```bash
curl -fsS 'https://cryptogenesis.duckdns.org/scan?chain=ethereum&address=0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
curl -fsS 'https://api.gopluslabs.io/api/v1/token_security/1?contract_addresses=0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
curl -fsS 'https://zarq.ai/v1/crypto/rating/ethereum'
```
