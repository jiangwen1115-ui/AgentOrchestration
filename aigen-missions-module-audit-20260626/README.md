# AIGEN Missions Module Audit - 2026-06-26

Agent: `codex-fbdb-20260626`

Scope: static audit of `targets/aigen-protocol/missions.py` for Task #22, focused on settlement, funding, and resolution behavior. No private keys, external account authorization, or live funds were used.

## Findings

### 1. Solana USDC missions can be created but cannot confirm funding

Severity: high

`create_mission()` accepts `reward_currency="USDC"` with `reward_chain="solana"` and stores the mission with `chain: "solana"` and `deposit_address: TREASURY_SOL`. However, `confirm_funding()` only has a Solana verification branch for native `SOL`. Non-SOL rewards fall through to the EVM lookup block, which indexes:

```python
rpc = {"base": "https://mainnet.base.org",
       "optimism": "https://mainnet.optimism.io"}[r["chain"]]
```

For a Solana USDC mission, `r["chain"] == "solana"`, so this raises `KeyError("solana")` and the function returns `{"error": "on-chain lookup failed: 'solana'"}`. Result: a funded SPL USDC mission remains stuck in `awaiting_funding`.

Code evidence: `missions.py` lines 381-383 accept Solana USDC, lines 492-499 persist Solana deposit details, lines 588-632 only handle native SOL, and lines 634-645 route everything else to EVM RPCs.

Expected fix: add SPL token transfer verification in `confirm_funding()` for `reward_chain == "solana"` and `reward_currency in SPL_TOKEN_MINTS`, checking token account balance delta or parsed token transfer to `TREASURY_SOL`.

### 2. First-valid-match can pay a winner when oracle verification is indeterminate

Severity: high for USDC/ETH/SOL missions, medium for AIGEN missions

`_oracle_verify()` documents `passed: None` as indeterminate and says it should be retried, not rejected. `_resolve_first_valid()` calls `_oracle_verify()`, but only rejects when `passed is False`. If `passed is None`, the matching submission is still assigned to `winner` and resolution proceeds.

For AIGEN first-valid missions, `_pay_winner()` currently blocks unverified `first_valid_match` payouts by returning net 0. For non-AIGEN missions, there is no equivalent block: the code can proceed to on-chain payout for a regex-matching proof even when the oracle was unavailable or inconclusive.

Code evidence: `missions.py` lines 1341-1351 define `None` as indeterminate; lines 1413-1421 choose a winner unless verification is explicitly false; lines 1423-1442 resolve/pay the winner.

Expected fix: in `_resolve_first_valid()`, treat `passed is None` like pending: store `oracle_check`, save state, and return a retryable error rather than selecting a winner. Only `passed is True` should win when real verification is required.

### 3. Oracle missions only inspect the first three submissions and can void despite later valid work

Severity: high

`_resolve_oracle()` sorts submissions by timestamp but iterates only `subs_sorted[:3]`. If the first three submissions fail and the fourth submission would pass, resolution never checks it. After the deadline, with no `pending_left`, the mission is voided and creator refunded.

This contradicts the function docstring: "First submission that PASSES real verification wins." The implementation is actually "first passing submission among the first three submissions wins."

Code evidence: `missions.py` lines 1354-1361 sort all submissions but slice to the first three; lines 1392-1399 void the mission when those checked submissions contain no pending/verified result.

Expected fix: iterate all non-final submissions, or make the first-three cap explicit in mission terms and avoid voiding while unchecked submissions remain.

### 4. Creator-judge timeout marks USDC/ETH consolation as claimable, but no claim endpoint exists

Severity: medium/high

When a `creator_judges` mission times out, non-AIGEN rewards set `consolation_claimable_amount` and `consolation_claimed` on each submission and comments say submitters can call `/missions/{id}/claim-consolation`. A repository-wide search found no implementation or route for `claim-consolation`.

Result: the resolution state advertises claimable consolation but provides no executable settlement path, leaving submitters' share stuck as metadata.

Code evidence: `missions.py` lines 1579-1605 create claimable fields and reference `/missions/{id}/claim-consolation`; `rg "claim-consolation|consolation_claim"` finds only those comments/fields and no function or API route.

Expected fix: implement the claim endpoint with idempotency, submitter authorization by agent id, wallet validation matching reward chain/currency, and payout through `_onchain_payout()`. Alternatively, remove the claimable promise and auto-refund/settle explicitly.

## Suggested Patch Direction

1. Move `fee_quote` and `funding_instructions` construction before `save(d)` in `create_mission()` so persisted mission detail matches the response.
2. Add SPL funding verification for Solana USDC/USDT/etc. in `confirm_funding()`.
3. Require `passed is True` for first-valid winner selection when `_oracle_verify()` is invoked.
4. Expand `_resolve_oracle()` beyond `subs_sorted[:3]`, or preserve unchecked submissions as pending instead of voiding.
5. Add `/missions/{id}/claim-consolation` or remove the claimable state for non-AIGEN creator-judge timeouts.

## Local Verification

Commands run:

```bash
rg -n "claim-consolation|consolation_claim" targets/aigen-protocol/missions.py targets/aigen-protocol -g'*.py'
nl -ba targets/aigen-protocol/missions.py | sed -n '430,565p'
nl -ba targets/aigen-protocol/missions.py | sed -n '570,646p'
nl -ba targets/aigen-protocol/missions.py | sed -n '1290,1465p'
nl -ba targets/aigen-protocol/missions.py | sed -n '1568,1612p'
```

No exploit execution, account authorization, or transaction signing was performed.
