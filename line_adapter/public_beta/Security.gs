var EDGE_ENVELOPE_VERSION_ = "line-public-beta-edge-envelope-v1";
var EDGE_MAX_AGE_SECONDS_ = 300;

function verifyEdgeEnvelope_(request) {
  if (!request || !request.envelope || !request.edge_signature) throw new Error("missing envelope");
  var envelope = request.envelope;
  if (envelope.schema_version !== EDGE_ENVELOPE_VERSION_) throw new Error("bad schema");
  var now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - Number(envelope.issued_at)) > EDGE_MAX_AGE_SECONDS_) throw new Error("old envelope");
  if (!/^dp_[0-9a-f]{64}$/.test(envelope.demo_principal_id)) throw new Error("bad principal");
  if (!/^[A-Za-z0-9_-]{8,128}$/.test(envelope.event_id)) throw new Error("bad event id");
  if (!/^[0-9a-f]{36}$/.test(envelope.nonce)) throw new Error("bad nonce");

  var secret = requiredScriptProperty_("DEMO_EDGE_GAS_SHARED_SECRET");
  var expected = hmacHex_(canonicalEnvelope_(envelope), secret);
  if (!timingSafeEqual_(expected, request.edge_signature)) throw new Error("bad signature");
  var cache = CacheService.getScriptCache();
  var nonceKey = "edge_nonce:" + envelope.nonce;
  if (cache.get(nonceKey)) throw new Error("replayed envelope");
  cache.put(nonceKey, "1", EDGE_MAX_AGE_SECONDS_);
  return envelope;
}

function canonicalEnvelope_(envelope) {
  return [
    envelope.schema_version,
    String(envelope.issued_at),
    envelope.nonce,
    envelope.event_id,
    envelope.demo_principal_id,
    envelope.reply_token || "",
    JSON.stringify(envelope.message)
  ].join("\n");
}

function hmacHex_(value, secret) {
  var bytes = Utilities.computeHmacSha256Signature(value, secret);
  return bytes.map(function(byte) {
    var unsigned = byte < 0 ? byte + 256 : byte;
    return ("0" + unsigned.toString(16)).slice(-2);
  }).join("");
}

function timingSafeEqual_(left, right) {
  if (typeof left !== "string" || typeof right !== "string" || left.length !== right.length) {
    return false;
  }
  var difference = 0;
  for (var index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function requiredScriptProperty_(name) {
  var value = PropertiesService.getScriptProperties().getProperty(name);
  if (!value) throw new Error("missing configuration");
  return value;
}
