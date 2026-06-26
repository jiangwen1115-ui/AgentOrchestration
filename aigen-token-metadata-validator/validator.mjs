const ZERO_WIDTH = /[\u200B-\u200D\uFEFF]/u;
const BIDI_OVERRIDE = /[\u202A-\u202E\u2066-\u2069]/u;
const CONTROL = /[\u0000-\u001F\u007F-\u009F]/u;
const REPLACEMENT = /\uFFFD/u;
const ADDRESS = /^0x[a-fA-F0-9]{40}$/;

const SEVERITY_WEIGHT = {
  info: 0,
  warning: 8,
  high: 22,
  critical: 35,
};

export function validateTokenRecords(records) {
  if (!Array.isArray(records)) {
    throw new TypeError("expected an array of token metadata records");
  }

  const reports = records.map(validateRecord);
  const crossChainFindings = findCrossChainMismatches(records);
  const findings = [
    ...reports.flatMap((report) => report.findings),
    ...crossChainFindings,
  ];
  const riskScore = Math.min(
    100,
    findings.reduce((sum, finding) => sum + SEVERITY_WEIGHT[finding.severity], 0),
  );

  return {
    ok: !findings.some((finding) => ["high", "critical"].includes(finding.severity)),
    riskScore,
    verdict: verdictForScore(riskScore),
    recordCount: records.length,
    findings,
    normalized: reports.map((report) => report.normalized),
  };
}

export function validateRecord(record, index = 0) {
  const findings = [];
  const chain = stringValue(record.chain);
  const address = stringValue(record.address);
  const name = stringValue(record.name);
  const symbol = stringValue(record.symbol);
  const decimals = Number(record.decimals);

  if (!chain) {
    findings.push(issue("warning", index, "chain_missing", "chain is missing"));
  }
  if (!ADDRESS.test(address)) {
    findings.push(issue("high", index, "address_invalid", "address must be a 20-byte hex EVM address"));
  }

  checkTextField(findings, index, "name", name, { maxLength: 80 });
  checkTextField(findings, index, "symbol", symbol, { maxLength: 24 });

  if (!Number.isInteger(decimals) || decimals < 0 || decimals > 255) {
    findings.push(issue("critical", index, "decimals_invalid", "decimals must be an integer from 0 to 255"));
  } else if (decimals > 36) {
    findings.push(issue("high", index, "decimals_extreme", "decimals above 36 are unusual and often unsafe for UI math"));
  }

  return {
    normalized: {
      chain,
      address: address.toLowerCase(),
      name: normalizeText(name),
      symbol: normalizeText(symbol),
      decimals,
      assetId: stringValue(record.asset_id || record.assetId || address).toLowerCase(),
    },
    findings,
  };
}

function findCrossChainMismatches(records) {
  const groups = new Map();
  records.forEach((record, index) => {
    const assetId = stringValue(record.asset_id || record.assetId || record.address).toLowerCase();
    if (!assetId) return;
    const group = groups.get(assetId) || [];
    group.push({ record, index });
    groups.set(assetId, group);
  });

  const findings = [];
  for (const [assetId, group] of groups.entries()) {
    if (group.length < 2) continue;
    for (const field of ["name", "symbol", "decimals"]) {
      const values = new Set(group.map(({ record }) => normalizeComparable(record[field])));
      if (values.size > 1) {
        findings.push({
          severity: field === "decimals" ? "high" : "warning",
          record: group.map(({ index }) => index),
          code: `cross_chain_${field}_mismatch`,
          message: `asset ${assetId} has inconsistent ${field} across chains`,
          values: [...values],
        });
      }
    }
  }
  return findings;
}

function checkTextField(findings, index, field, value, options) {
  if (!value) {
    findings.push(issue("high", index, `${field}_missing`, `${field} is missing`));
    return;
  }
  if (value.length > options.maxLength) {
    findings.push(issue("warning", index, `${field}_too_long`, `${field} is unusually long`));
  }
  if (CONTROL.test(value)) {
    findings.push(issue("critical", index, `${field}_control_chars`, `${field} contains control characters`));
  }
  if (ZERO_WIDTH.test(value)) {
    findings.push(issue("high", index, `${field}_zero_width`, `${field} contains zero-width characters`));
  }
  if (BIDI_OVERRIDE.test(value)) {
    findings.push(issue("critical", index, `${field}_bidi_override`, `${field} contains bidirectional override characters`));
  }
  if (REPLACEMENT.test(value)) {
    findings.push(issue("high", index, `${field}_replacement_char`, `${field} contains unicode replacement characters`));
  }
  if (value !== normalizeText(value)) {
    findings.push(issue("warning", index, `${field}_normalizes`, `${field} changes under NFKC normalization`));
  }
}

function issue(severity, record, code, message) {
  return { severity, record, code, message };
}

function normalizeText(value) {
  return stringValue(value).normalize("NFKC").trim();
}

function normalizeComparable(value) {
  if (typeof value === "number") return String(value);
  return normalizeText(value).toLowerCase();
}

function stringValue(value) {
  return typeof value === "string" ? value : "";
}

function verdictForScore(score) {
  if (score >= 50) return "BLOCK";
  if (score >= 25) return "REVIEW";
  if (score > 0) return "CAUTION";
  return "PASS";
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const inputPath = process.argv[2];
  if (!inputPath) {
    console.error("Usage: node validator.mjs <tokens.json>");
    process.exit(2);
  }
  const { readFileSync } = await import("node:fs");
  const records = JSON.parse(readFileSync(inputPath, "utf8"));
  console.log(JSON.stringify(validateTokenRecords(records), null, 2));
}
