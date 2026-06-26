#!/usr/bin/env python3
"""Reproduce mission-module issues against an isolated temp ledger.

This script imports targets/aigen-protocol/missions.py but rewires its
MISSIONS_FILE and LEDGER paths to a temporary directory. It does not touch
production AIGEN state or real wallets.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import time
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MISSIONS_PY = ROOT / "targets" / "aigen-protocol" / "missions.py"


def load_module():
    spec = importlib.util.spec_from_file_location("audit_missions", MISSIONS_PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def isolate(mod, td: Path, ledger: dict | None = None):
    mod.MISSIONS_FILE = td / "missions.json"
    mod.LEDGER = td / "ledger.json"
    mod._notify_subscribers_on_create = lambda mission: None
    mod._fire_webhook = lambda url, payload: None
    mod._send_email = lambda to_addr, subject, body: None
    mod._elo = lambda agent_id: 1500
    if ledger is None:
        ledger = {"agents": {}, "total_distributed": 0}
    mod.LEDGER.write_text(json.dumps(ledger))


def result(name: str, observed: bool, details: dict):
    return {"name": name, "bug_observed": observed, "details": details}


def post_debit_validation_drains_balance():
    mod = load_module()
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        isolate(
            mod,
            td,
            {
                "agents": {
                    "alice": {
                        "balance": 100,
                        "total_earned": 100,
                        "actions": 0,
                        "first_seen": 0,
                    }
                },
                "total_distributed": 100,
            },
        )
        before = json.loads(mod.LEDGER.read_text())["agents"]["alice"]["balance"]
        out = mod.create_mission(
            "alice",
            "Invalid category",
            "Should fail before charging.",
            10,
            "peer_vote",
            category="not-a-category",
        )
        after = json.loads(mod.LEDGER.read_text())["agents"]["alice"]["balance"]
        return result(
            "post-debit validation drains AIGEN",
            "error" in out and before == 100 and after == 85 and not mod.MISSIONS_FILE.exists(),
            {"return": out, "balance_before": before, "balance_after": after},
        )


def returned_fee_and_funding_metadata_not_persisted():
    mod = load_module()
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        isolate(mod, td)
        out = mod.create_mission(
            "creator",
            "USDC funding UX",
            "Funding instructions should survive a later GET.",
            10_000,
            "peer_vote",
            reward_currency="USDC",
            reward_chain="base",
        )
        stored = mod.load()["missions"][0]
        return result(
            "fee_quote/funding_instructions returned but not persisted",
            "fee_quote" in out
            and "funding_instructions" in out
            and "fee_quote" not in stored
            and "funding_instructions" not in stored,
            {
                "returned_has_fee_quote": "fee_quote" in out,
                "returned_has_funding_instructions": "funding_instructions" in out,
                "stored_has_fee_quote": "fee_quote" in stored,
                "stored_has_funding_instructions": "funding_instructions" in stored,
            },
        )


def solana_usdc_can_be_created_but_not_confirmed():
    mod = load_module()
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        isolate(mod, td)
        out = mod.create_mission(
            "creator",
            "Solana USDC funding",
            "Creation accepts USDC on Solana.",
            10_000,
            "peer_vote",
            reward_currency="USDC",
            reward_chain="solana",
        )
        fake_web3 = types.ModuleType("web3")
        fake_web3.Web3 = object
        sys.modules["web3"] = fake_web3
        confirm = mod.confirm_funding(out["id"], "1" * 64)
        return result(
            "USDC-on-Solana creation has no confirm_funding path",
            out.get("status") == "awaiting_funding"
            and out.get("reward", {}).get("chain") == "solana"
            and "on-chain lookup failed" in confirm.get("error", "")
            and "solana" in confirm.get("error", ""),
            {"created_status": out.get("status"), "confirm_return": confirm},
        )


def first_valid_pays_when_oracle_is_indeterminate():
    mod = load_module()
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        isolate(mod, td)
        mission = {
            "id": "mis_indeterminate",
            "creator": "creator",
            "title": "First valid real-money race",
            "description": "A matching regex should not pay if oracle is indeterminate.",
            "category": "code",
            "mission_type": "freeform",
            "type_params": {},
            "webhook_url": "",
            "notify_email": "",
            "reward": {
                "currency": "USDC",
                "amount": 10_000,
                "chain": "base",
                "deposit_address": mod.TREASURY,
                "deposit_tx": "0x" + "a" * 64,
                "deposit_confirmed_at": int(time.time()),
                "payout_tx": None,
                "payout_at": None,
            },
            "reward_aigen": 0,
            "spam_fee_burned": 0,
            "verification_type": "first_valid_match",
            "verification_params": {"regex": "^OK$"},
            "min_submitter_elo": 0,
            "created_at": int(time.time()) - 10,
            "deadline": int(time.time()) + 3600,
            "status": "open",
            "submissions": [],
            "resolution": None,
        }
        mod.MISSIONS_FILE.write_text(
            json.dumps(
                {
                    "missions": [mission],
                    "total": 1,
                    "resolved": 0,
                    "voided": 0,
                    "lifetime_reward_aigen_escrowed": 0,
                    "lifetime_reward_aigen_paid": 0,
                    "lifetime_spam_fees_burned": 0,
                }
            )
        )
        mod._oracle_verify = lambda m, s: {
            "passed": None,
            "reason": "verifier unavailable",
        }
        mod._onchain_payout = lambda currency, chain, wallet, amount: {
            "tx_hash": "0x" + "b" * 64
        }
        out = mod.submit(
            "bob",
            "mis_indeterminate",
            "OK",
            submitter_wallet="0x" + "1" * 40,
        )
        stored = mod.load()["missions"][0]
        oracle_check = stored["submissions"][0]["oracle_check"]
        return result(
            "first_valid_match pays real-money winner on indeterminate oracle",
            out.get("instant_resolved") is True
            and stored.get("status") == "resolved"
            and oracle_check.get("passed") is None
            and stored.get("resolution", {}).get("payout", {}).get("ok") is True,
            {
                "submit_return": out,
                "stored_status": stored.get("status"),
                "oracle_check": oracle_check,
                "resolution": stored.get("resolution"),
            },
        )


def resolved_missions_are_not_idempotent():
    mod = load_module()
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        isolate(mod, td)
        mod.MISSIONS_FILE.write_text(
            json.dumps(
                {
                    "missions": [
                        {
                            "id": "mis_resolved",
                            "creator": "creator",
                            "title": "Already resolved",
                            "description": "resolve() docstring says idempotent.",
                            "reward": {"currency": "AIGEN", "amount": 10},
                            "verification_type": "peer_vote",
                            "deadline": int(time.time()) - 10,
                            "status": "resolved",
                            "submissions": [],
                            "resolution": {"type": "peer_vote", "outcome": "WINNER"},
                        }
                    ],
                    "total": 1,
                    "resolved": 1,
                    "voided": 0,
                    "lifetime_reward_aigen_escrowed": 0,
                    "lifetime_reward_aigen_paid": 0,
                    "lifetime_spam_fees_burned": 0,
                }
            )
        )
        out = mod.resolve("mis_resolved")
        return result(
            "resolve() docstring says idempotent but returns error for resolved missions",
            "error" in out and out.get("resolution", {}).get("outcome") == "WINNER",
            {"resolve_return": out},
        )


def main():
    checks = [
        post_debit_validation_drains_balance(),
        returned_fee_and_funding_metadata_not_persisted(),
        solana_usdc_can_be_created_but_not_confirmed(),
        first_valid_pays_when_oracle_is_indeterminate(),
        resolved_missions_are_not_idempotent(),
    ]
    print(json.dumps({"target": str(MISSIONS_PY), "checks": checks}, indent=2))
    if not all(c["bug_observed"] for c in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
