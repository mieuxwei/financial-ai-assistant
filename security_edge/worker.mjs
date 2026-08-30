import {
  deriveDemoPrincipal,
  signEdgePayload,
  verifyLineSignature,
} from "./line_security.mjs";

const MAX_BODY_BYTES = 128 * 1024;
const MAX_MESSAGE_LENGTH = 1000;

export default {
  async fetch(request, env, context) {
    return handleRequest(request, env, fetch, context);
  },
};

export async function handleRequest(request, env, fetchImpl, executionContext = null) {
  if (request.method !== "POST") return safeResponse("method not allowed", 405);
  if (!requiredEnvironment(env)) return safeResponse("service unavailable", 503);

  const declaredLength = Number(request.headers.get("content-length") || "0");
  if (declaredLength > MAX_BODY_BYTES) return safeResponse("payload too large", 413);
  const rawBody = await request.text();
  if (new TextEncoder().encode(rawBody).byteLength > MAX_BODY_BYTES) {
    return safeResponse("payload too large", 413);
  }
  const signature = request.headers.get("x-line-signature");
  if (!(await verifyLineSignature(rawBody, signature, env.LINE_DEMO_CHANNEL_SECRET))) {
    return safeResponse("unauthorized", 401);
  }

  let payload;
  try {
    payload = JSON.parse(rawBody);
  } catch {
    return safeResponse("invalid request", 400);
  }
  if (!Array.isArray(payload.events)) return safeResponse("invalid request", 400);

  const processing = (async () => {
    for (const event of payload.events) {
      const envelope = await normalizeVerifiedEvent(event, env);
      if (!envelope) continue;
      const signedPayload = JSON.stringify(envelope);
      const edgeSignature = await signEdgePayload(
        signedPayload,
        env.DEMO_EDGE_GAS_SHARED_SECRET,
      );
      const forwarded = await fetchImpl(env.DEMO_GAS_WEB_APP_URL, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ signed_payload: signedPayload, edge_signature: edgeSignature }),
        redirect: "follow",
      });
      console.log(`demo_gas_http_status=${forwarded.status}`);
      if (!forwarded.ok) throw new Error("demo GAS rejected verified envelope");
      const gasResult = await forwarded.json();
      console.log(`demo_gas_application_status=${String(gasResult?.status || "missing")}`);
      if (gasResult?.status !== "ok") throw new Error("demo GAS rejected verified envelope");
    }
  })();

  if (executionContext && typeof executionContext.waitUntil === "function") {
    executionContext.waitUntil(
      processing.catch(() => console.error("demo_gas_background_status=failed")),
    );
    return safeResponse("ok", 200);
  }

  try {
    await processing;
  } catch {
    return safeResponse("temporary processing failure", 502);
  }
  return safeResponse("ok", 200);
}

async function normalizeVerifiedEvent(event, env) {
  const rawLineUserId = event?.source?.userId;
  const eventId = event?.webhookEventId;
  if (typeof rawLineUserId !== "string" || typeof eventId !== "string") return null;
  const message = normalizedMessage(event);
  if (message === null) return null;
  return {
    schema_version: "line-public-beta-edge-envelope-v1",
    issued_at: Math.floor(Date.now() / 1000),
    nonce: randomToken(),
    event_id: eventId.slice(0, 128),
    demo_principal_id: await deriveDemoPrincipal(rawLineUserId, env.DEMO_IDENTITY_SECRET),
    reply_token: typeof event.replyToken === "string" ? event.replyToken.slice(0, 256) : null,
    message,
  };
}

function normalizedMessage(event) {
  if (event.type === "follow") return { type: "follow" };
  if (event.type === "message" && event.message?.type === "text") {
    return { type: "text", text: String(event.message.text || "").slice(0, MAX_MESSAGE_LENGTH) };
  }
  if (event.type === "postback") {
    return { type: "postback", data: String(event.postback?.data || "").slice(0, MAX_MESSAGE_LENGTH) };
  }
  return null;
}

function randomToken() {
  const bytes = crypto.getRandomValues(new Uint8Array(18));
  return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function requiredEnvironment(env) {
  const secretsReady = [
    env.LINE_DEMO_CHANNEL_SECRET,
    env.DEMO_IDENTITY_SECRET,
    env.DEMO_EDGE_GAS_SHARED_SECRET,
  ].every((value) => typeof value === "string" && value.length >= 32);
  return secretsReady && /^https:\/\//.test(env.DEMO_GAS_WEB_APP_URL || "");
}

function safeResponse(message, status) {
  return new Response(JSON.stringify({ status: message }), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}
