const encoder = new TextEncoder();

export async function verifyLineSignature(rawBody, suppliedSignature, channelSecret) {
  if (!suppliedSignature || !channelSecret) return false;
  const expected = await hmacBase64(channelSecret, rawBody);
  return timingSafeEqual(expected, suppliedSignature);
}

export async function deriveDemoPrincipal(rawLineUserId, identitySecret) {
  if (!rawLineUserId || !identitySecret) throw new Error("identity input is unavailable");
  return `dp_${await hmacHex(identitySecret, rawLineUserId)}`;
}

export async function signEdgeEnvelope(envelope, sharedSecret) {
  return signEdgePayload(JSON.stringify(envelope), sharedSecret);
}

export async function signEdgePayload(signedPayload, sharedSecret) {
  return hmacHex(sharedSecret, signedPayload);
}

export function canonicalEnvelope(envelope) {
  return [
    envelope.schema_version,
    String(envelope.issued_at),
    envelope.nonce,
    envelope.event_id,
    envelope.demo_principal_id,
    envelope.reply_token || "",
    JSON.stringify(envelope.message),
  ].join("\n");
}

export function timingSafeEqual(left, right) {
  if (typeof left !== "string" || typeof right !== "string" || left.length !== right.length) {
    return false;
  }
  const leftBytes = encoder.encode(left);
  const rightBytes = encoder.encode(right);
  if (typeof crypto.subtle.timingSafeEqual === "function") {
    return crypto.subtle.timingSafeEqual(leftBytes, rightBytes);
  }
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

async function hmacBase64(secret, value) {
  const bytes = await hmac(secret, value);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

async function hmacHex(secret, value) {
  const bytes = await hmac(secret, value);
  return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function hmac(secret, value) {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, encoder.encode(value)));
}
