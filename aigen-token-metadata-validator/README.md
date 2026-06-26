# AIGEN Token Metadata Validator

Small dependency-free validator for token metadata collected across EVM chains.

It flags:

- invalid EVM addresses
- missing name, symbol, chain, or decimals
- control characters, zero-width characters, bidi override characters, and replacement characters
- NFKC normalization changes that can hide spoofed symbols
- unusual decimals values
- cross-chain name, symbol, or decimals mismatches grouped by `asset_id`

## Usage

```bash
node validator.mjs tokens.json
```

Input:

```json
[
  {
    "asset_id": "usdc",
    "chain": "base",
    "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "name": "USD Coin",
    "symbol": "USDC",
    "decimals": 6
  }
]
```

Output includes `ok`, `riskScore`, `verdict`, normalized records, and structured findings.

## Verification

```bash
npm test
```
