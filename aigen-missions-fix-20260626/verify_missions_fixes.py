#!/usr/bin/env python3
"""Regression checks for the AIGEN missions.py safety patch.

The script imports the local target module, redirects its storage paths into a
temporary directory, and mocks the Solana RPC response. It never touches live
mission state, live ledger state, private keys, or the network.
"""
import importlib.util
import json
import tempfile
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MISSIONS_PATH = ROOT / "targets" / "aigen-protocol" / "missions.py"


def load_module():
    spec = importlib.util.spec_from_file_location("patched_missions", MISSIONS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_ok(condition, message):
    if not condition:
        raise AssertionError(message)


def configure_temp_state(module, tmpdir):
    module.MISSIONS_FILE = Path(tmpdir) / "missions.json"
    module.LEDGER = Path(tmpdir) / "ledger.json"
    module.SUBSCRIBERS_FILE = Path(tmpdir) / "subscribers.json"
    module._notify_subscribers_on_create = lambda mission: None
    module.LEDGER.write_text(json.dumps({
        "agents": {
            "creator": {"balance": 100, "total_earned": 0, "actions": 0},
            "worker": {"balance": 0, "total_earned": 0, "actions": 0},
            "worker2": {"balance": 0, "total_earned": 0, "actions": 0},
            "treasury": {"balance": 0, "total_earned": 0, "actions": 0},
        },
        "total_distributed": 0,
    }))


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_pre_debit_validation(module):
    before = module._balance("creator")
    result = module.create_mission(
        "creator", "Invalid category", "Should fail before debit",
        10, "peer_vote", category="not-a-category",
    )
    after = module._balance("creator")
    assert_ok("error" in result, "invalid category should be rejected")
    assert_ok(before == 100 and after == 100, "validation failure must not debit AIGEN")
    assert_ok(not module.MISSIONS_FILE.exists(), "failed create must not persist a mission")


def test_creation_metadata_persisted(module):
    created = module.create_mission(
        "creator", "Base USDC mission", "Check stored create metadata",
        10_000, "creator_judges", reward_currency="USDC", reward_chain="base",
    )
    assert_ok(created.get("id"), f"USDC mission create failed: {created}")
    stored = module.load()["missions"][-1]
    assert_ok(stored["id"] == created["id"], "stored mission id should match return value")
    assert_ok(stored.get("fee_quote") == created.get("fee_quote"), "fee_quote should be persisted")
    assert_ok(
        stored.get("funding_instructions") == created.get("funding_instructions"),
        "funding_instructions should be persisted",
    )
    assert_ok(
        stored["funding_instructions"]["amount_base_units"] == 10_000,
        "funding instructions should include base units",
    )


def test_solana_spl_confirm(module):
    created = module.create_mission(
        "creator", "Solana USDC mission", "Check SPL deposit confirmation",
        10_000, "creator_judges", reward_currency="USDC", reward_chain="solana",
    )
    assert_ok(created.get("id"), f"Solana USDC mission create failed: {created}")

    mint = module.SPL_TOKEN_MINTS["USDC"]
    payload = {
        "result": {
            "meta": {
                "err": None,
                "preTokenBalances": [
                    {
                        "accountIndex": 7,
                        "mint": mint,
                        "owner": module.TREASURY_SOL,
                        "uiTokenAmount": {"amount": "2000"},
                    }
                ],
                "postTokenBalances": [
                    {
                        "accountIndex": 7,
                        "mint": mint,
                        "owner": module.TREASURY_SOL,
                        "uiTokenAmount": {"amount": "12000"},
                    }
                ],
            }
        }
    }

    original_urlopen = urllib.request.urlopen
    urllib.request.urlopen = lambda req, timeout=15: FakeResponse(payload)
    try:
        result = module.confirm_funding(created["id"], "2" * 88)
    finally:
        urllib.request.urlopen = original_urlopen

    assert_ok(result.get("ok") is True, f"SPL funding should confirm: {result}")
    stored = next(m for m in module.load()["missions"] if m["id"] == created["id"])
    assert_ok(stored["status"] == "open", "confirmed SPL mission should open")
    assert_ok(stored["reward"]["deposit_tx"] == "2" * 88, "deposit tx should be stored")


def test_first_valid_pending_does_not_pay(module):
    module._oracle_verify = lambda mission, submission: {
        "passed": None,
        "reason": "test verifier indeterminate",
    }
    created = module.create_mission(
        "creator", "First valid pending", "Do not pay on indeterminate oracle",
        10, "first_valid_match", verification_params={"regex": "PASS"},
    )
    assert_ok(created.get("id"), f"first_valid create failed: {created}")
    submitted = module.submit("worker", created["id"], "PASS")
    assert_ok(submitted.get("ok") is True, f"submission failed: {submitted}")
    assert_ok("instant_resolved" not in submitted, "indeterminate oracle must not instant-resolve")

    stored = next(m for m in module.load()["missions"] if m["id"] == created["id"])
    sub = stored["submissions"][0]
    assert_ok(stored["status"] == "open", "mission should remain open while oracle is pending")
    assert_ok(sub["status"] == "pending", "submission should remain pending")
    assert_ok(sub["oracle_check"]["passed"] is None, "oracle_check should persist passed=None")
    assert_ok(module._balance("worker") == 0, "worker must not be paid while verification is pending")

    resolved = module.resolve(created["id"])
    assert_ok(resolved.get("pending") is True, f"resolve should return pending: {resolved}")


def test_resolve_idempotent(module):
    module._oracle_verify = lambda mission, submission: {
        "passed": True,
        "reason": "test verifier passed",
    }
    created = module.create_mission(
        "creator", "First valid pass", "Resolved mission should be idempotent",
        10, "first_valid_match", verification_params={"regex": "PASS"},
    )
    assert_ok(created.get("id"), f"first_valid create failed: {created}")
    submitted = module.submit("worker2", created["id"], "PASS")
    assert_ok(submitted.get("instant_resolved") is True, f"expected instant resolution: {submitted}")

    repeated = module.resolve(created["id"])
    assert_ok(repeated.get("ok") is True, f"repeat resolve should be ok: {repeated}")
    assert_ok(repeated.get("already_resolved") is True, "repeat resolve should mark already_resolved")
    assert_ok(repeated.get("resolution", {}).get("winner_agent_id") == "worker2", "prior winner should be returned")


def main():
    module = load_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        configure_temp_state(module, tmpdir)
        test_pre_debit_validation(module)
        test_creation_metadata_persisted(module)
        test_solana_spl_confirm(module)
        test_first_valid_pending_does_not_pay(module)
        test_resolve_idempotent(module)
    print("missions.py regression checks passed")


if __name__ == "__main__":
    main()
