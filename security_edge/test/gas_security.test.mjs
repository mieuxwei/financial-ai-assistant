import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

import { signEdgeEnvelope } from "../line_security.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(
  path.resolve(here, "../../line_adapter/public_beta/Security.gs"),
  "utf8",
);
const secret = "edge-gas-secret-for-tests-only-32bytes";

function runtime() {
  const values = new Map();
  const context = {
    Date,
    JSON,
    Math,
    Number,
    RegExp,
    String,
    Error,
    PropertiesService: {
      getScriptProperties: () => ({ getProperty: (name) => (name === "DEMO_EDGE_GAS_SHARED_SECRET" ? secret : null) }),
    },
    CacheService: {
      getScriptCache: () => ({
        get: (key) => values.get(key) || null,
        put: (key, value) => values.set(key, value),
      }),
    },
    Utilities: {
      computeHmacSha256Signature: (value, key) => [...crypto.createHmac("sha256", key).update(value).digest()],
    },
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  return context;
}

function envelope(issuedAt = Math.floor(Date.now() / 1000)) {
  return {
    schema_version: "line-public-beta-edge-envelope-v1",
    issued_at: issuedAt,
    nonce: "0123456789abcdef0123456789abcdef0123",
    event_id: "evt_1234567890abcdef",
    demo_principal_id: `dp_${"a".repeat(64)}`,
    reply_token: "reply-token",
    message: { type: "text", text: "主選單" },
  };
}

test("Demo GAS accepts a fresh correctly signed envelope once", async () => {
  const context = runtime();
  const value = envelope();
  const request = { envelope: value, edge_signature: await signEdgeEnvelope(value, secret) };
  assert.equal(context.verifyEdgeEnvelope_(request).event_id, value.event_id);
  assert.throws(() => context.verifyEdgeEnvelope_(request), /replayed envelope/);
});

test("Demo GAS rejects old and badly signed envelopes", async () => {
  const current = envelope();
  const bad = { envelope: current, edge_signature: "0".repeat(64) };
  assert.throws(() => runtime().verifyEdgeEnvelope_(bad), /bad signature/);

  const old = envelope(Math.floor(Date.now() / 1000) - 301);
  const oldRequest = { envelope: old, edge_signature: await signEdgeEnvelope(old, secret) };
  assert.throws(() => runtime().verifyEdgeEnvelope_(oldRequest), /old envelope/);
});
