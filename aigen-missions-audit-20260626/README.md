# AIGEN missions.py Audit

Generated: 2026-06-26T08:13:36Z

Agent: `codex-fbdb-20260626`

Target: `targets/aigen-protocol/missions.py`

Target commit observed locally: `01ea3f33e423b08442d34bb165c9d5a072bbf3b5`

This is a Task #22-style code review of the AIGEN `/missions` module. The audit focuses on ledger safety, funding activation, resolver behavior, and real-money payout paths.

## Reproduction

Run from the workspace root:

```bash
python3 work/aigen-missions-audit-20260626/repro_missions_bugs.py
```

The script imports `missions.py`, rewires `MISSIONS_FILE` and `LEDGER` to a temporary directory, disables side-effect notifications, and monkeypatches external payout/verifier calls where needed. It does not touch production AIGEN state or real wallets.

Latest local run result: all 5 checks returned `"bug_observed": true`.

## Findings

### 1. AIGEN balance can be debited before create_mission rejects invalid fields

Severity: high

Lines: `missions.py:430-479`

`create_mission()` debits AIGEN reward escrow and the spam fee before validating `webhook_url`, `notify_email`, `category`, `mission_type`, and `type_params`. If any later validation fails, the function returns an error without rolling back the debit and without saving a mission.

Repro evidence:

```json
{
  "return": {"error": "category must be one of [...]"},
  "balance_before": 100,
  "balance_after": 85
}
```

Impact: a malformed request can burn or escrow creator funds while returning an error and creating no mission.

Fix direction: perform all non-mutating validation before `_debit()`, or wrap debits in a transaction/rollback block that covers every later validation error.

### 2. fee_quote and funding_instructions are returned but not persisted

Severity: medium

Lines: `missions.py:520-562`

`create_mission()` saves the mission at line 526, then adds `fee_quote` and, for non-AIGEN rewards, `funding_instructions` to the in-memory return object. A later `get_mission()` or persisted JSON read will not include those fields.

Repro evidence:

```json
{
  "returned_has_fee_quote": true,
  "returned_has_funding_instructions": true,
  "stored_has_fee_quote": false,
  "stored_has_funding_instructions": false
}
```

Impact: creators who refresh or fetch the mission after creation lose the deposit address/instructions and fee quote that the API promised.

Fix direction: compute and attach `fee_quote` and `funding_instructions` before `d["missions"].append(m)` and `save(d)`, or save again after adding them.

### 3. USDC-on-Solana missions can be created but cannot be confirmed

Severity: high

Lines: `missions.py:371-386`, `missions.py:588-645`

`create_mission()` explicitly accepts `reward_currency="USDC"` with `reward_chain="solana"`, and also forces SPL currencies onto Solana. But `confirm_funding()` only has a Solana path for native `SOL`. Non-SOL Solana rewards fall through to the EVM RPC map, which only contains `base` and `optimism`.

Repro evidence:

```json
{
  "created_status": "awaiting_funding",
  "confirm_return": {"error": "on-chain lookup failed: 'solana'"}
}
```

Impact: creators can be instructed to fund Solana USDC/SPL missions that the backend cannot activate.

Fix direction: add SPL transfer verification for Solana USDC/SPL deposits, or reject those reward/chain combinations until verification exists.

### 4. first_valid_match can pay a real-money winner when oracle verification is indeterminate

Severity: critical

Lines: `missions.py:1341-1351`, `missions.py:1405-1424`

`_oracle_verify()` documents `passed=None` as indeterminate and says it should be retried, not rejected. `_resolve_oracle()` handles that correctly. `_resolve_first_valid()` does not: it rejects only `passed is False`, so `passed is None` still selects a winner and pays them. For USDC/ETH/SOL/SPL missions, `_pay_winner()` has no first-valid anti-farm block, so this can pay real funds if the verifier is down.

Repro evidence:

```json
{
  "instant_resolved": true,
  "oracle_check": {"passed": null, "reason": "verifier unavailable"},
  "payout": {"ok": true, "currency": "USDC", "net": 9950}
}
```

Impact: temporary verifier failure can convert a regex match into a paid real-money win.

Fix direction: in `_resolve_first_valid()`, treat `passed is None` as pending/retry and do not set `winner`. Only pay when either the mission explicitly requires regex-only verification or the oracle returns `passed is True`.

### 5. resolve() claims idempotency but returns an error for resolved missions

Severity: low

Lines: `missions.py:1289-1297`

The docstring says already-resolved missions return the prior outcome. The implementation returns `{"error": "mission is resolved", "resolution": ...}` for any non-open mission.

Repro evidence:

```json
{
  "resolve_return": {
    "error": "mission is resolved",
    "resolution": {"type": "peer_vote", "outcome": "WINNER"}
  }
}
```

Impact: clients and automation may treat successful prior resolutions as failures, causing noisy retries or false alerts.

Fix direction: special-case `status == "resolved"` and return `{"ok": true, "already_resolved": true, "resolution": ...}`.

## Additional Note

`missions.py:1579-1604` describes a future `/missions/{id}/claim-consolation` path for USDC/ETH creator-judge timeouts, and marks submitters as claimable, but a repository-wide search did not find an implementation of that route/function. I did not include it as a primary repro check because it requires route-level confirmation, but it is worth reviewing before relying on non-AIGEN creator-judge consolation payouts.
