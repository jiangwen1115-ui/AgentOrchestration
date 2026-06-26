# AIGEN missions.py bugfix patch

Agent: `codex-fbdb-20260626`

Date: 2026-06-26

This package turns the previously reported `missions.py` audit findings into a
concrete patch plus regression checks. It focuses on reward safety, funding
activation, and deterministic resolution behavior.

## Files

- `missions_fix.patch` - patch against `targets/aigen-protocol/missions.py`.
- `verify_missions_fixes.py` - isolated regression checks using temporary
  mission/ledger files and a mocked Solana RPC response.

## Fixed behaviors

1. AIGEN creator balances are no longer debited before optional `webhook_url`,
   `notify_email`, `category`, `mission_type`, and `type_params` validation.
2. `fee_quote` and `funding_instructions` are now persisted in stored mission
   state, not only returned to the caller.
3. Solana SPL rewards such as USDC-on-Solana can be confirmed by checking the
   treasury-owned token balance delta in `preTokenBalances`/`postTokenBalances`.
4. `first_valid_match` only pays after `_oracle_verify(...).passed is True`.
   `None` is treated as pending and saved as an `oracle_check`, not as a win.
5. `resolve()` now behaves idempotently for already `resolved` or `voided`
   missions by returning the existing resolution with `already_resolved`.

## Verification

Run from the workspace root:

```bash
python3 work/aigen-missions-fix-20260626/verify_missions_fixes.py
```

Expected output:

```text
missions.py regression checks passed
```

Also checked:

```bash
python3 -m py_compile targets/aigen-protocol/missions.py
python3 -m py_compile work/aigen-missions-fix-20260626/verify_missions_fixes.py
```

The regression script does not touch live AIGEN state, private keys, or the
network. It redirects storage paths to a temporary directory and mocks Solana
RPC.
