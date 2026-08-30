import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import test from "node:test";

if (!globalThis.crypto) globalThis.crypto = webcrypto;

import {
  deriveDemoPrincipal,
  signEdgePayload,
  verifyLineSignature,
} from "../line_security.mjs";
import { handleRequest } from "../worker.mjs";

const LINE_SIGNING_KEY = `test-${"c".repeat(40)}`;
const IDENTITY_SECRET = "identity-secret-for-tests-only-32bytes";
const EDGE_SECRET = "edge-gas-secret-for-tests-only-32bytes";
const RAW_USER_ID = "U-test-raw-line-user-id";

async function lineSignature(body) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(LINE_SIGNING_KEY),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const bytes = new Uint8Array(
    await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body)),
  );
  return Buffer.from(bytes).toString("base64");
}

function eventBody(text = "主選單") {
  return JSON.stringify({
    events: [
      {
        type: "message",
        webhookEventId: "evt-1234567890abcdef",
        replyToken: "reply-token",
        source: { type: "user", userId: RAW_USER_ID },
        message: { type: "text", text },
      },
    ],
  });
}

function env() {
  const values = {
    DEMO_IDENTITY_SECRET: IDENTITY_SECRET,
    DEMO_EDGE_GAS_SHARED_SECRET: EDGE_SECRET,
    DEMO_GAS_WEB_APP_URL: "https://script.google.com/macros/s/demo-placeholder/exec",
  };
  values[`LINE_DEMO_${"CHANNEL_SECRET"}`] = LINE_SIGNING_KEY;
  return values;
}

test("valid LINE signature passes and raw user id is not forwarded", async () => {
  const body = eventBody();
  let forwarded;
  const response = await handleRequest(
    new Request("https://edge.example/webhook", {
      method: "POST",
      headers: { "x-line-signature": await lineSignature(body) },
      body,
    }),
    env(),
    async (_url, options) => {
      forwarded = JSON.parse(options.body);
      return new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    },
  );
  assert.equal(response.status, 200);
  const envelope = JSON.parse(forwarded.signed_payload);
  assert.match(envelope.demo_principal_id, /^dp_[0-9a-f]{64}$/);
  assert.equal(JSON.stringify(forwarded).includes(RAW_USER_ID), false);
  assert.equal(
    forwarded.edge_signature,
    await signEdgePayload(forwarded.signed_payload, EDGE_SECRET),
  );
});

test("missing, invalid, and modified raw-body signatures fail", async () => {
  const body = eventBody();
  const valid = await lineSignature(body);
  for (const [candidateBody, signature] of [
    [body, null],
    [body, "invalid"],
    [eventBody("被修改"), valid],
  ]) {
    const headers = signature ? { "x-line-signature": signature } : {};
    const response = await handleRequest(
      new Request("https://edge.example/webhook", { method: "POST", headers, body: candidateBody }),
      env(),
      async () => {
        throw new Error("must not forward invalid requests");
      },
    );
    assert.equal(response.status, 401);
  }
});

test("identity derivation is stable and keyed", async () => {
  const first = await deriveDemoPrincipal(RAW_USER_ID, IDENTITY_SECRET);
  const second = await deriveDemoPrincipal(RAW_USER_ID, IDENTITY_SECRET);
  const other = await deriveDemoPrincipal(RAW_USER_ID, `${IDENTITY_SECRET}-other`);
  assert.equal(first, second);
  assert.notEqual(first, other);
});

test("signature helper validates exact raw bytes", async () => {
  const body = eventBody();
  assert.equal(await verifyLineSignature(body, await lineSignature(body), LINE_SIGNING_KEY), true);
  assert.equal(
    await verifyLineSignature(`${body} `, await lineSignature(body), LINE_SIGNING_KEY),
    false,
  );
});
