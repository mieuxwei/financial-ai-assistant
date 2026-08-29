function backendRequest_(principalId, method, path, payload, idempotencyKey) {
  var baseUrl = requiredScriptProperty_("DEMO_FASTAPI_BASE_URL").replace(/\/$/, "");
  if (!/^https:\/\//.test(baseUrl)) throw new Error("backend must use HTTPS");
  var headers = {
    "Authorization": "Bearer " + requiredScriptProperty_("DEMO_GAS_SERVICE_TOKEN"),
    "X-Demo-Principal-ID": principalId
  };
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
  var options = {
    method: method.toLowerCase(),
    headers: headers,
    muteHttpExceptions: true,
    followRedirects: false
  };
  if (payload !== undefined && payload !== null) {
    options.contentType = "application/json";
    options.payload = JSON.stringify(payload);
  }
  var response = UrlFetchApp.fetch(baseUrl + "/api/v1/demo" + path, options);
  var status = response.getResponseCode();
  if (status < 200 || status >= 300) throw new Error("backend request failed");
  return JSON.parse(response.getContentText() || "{}");
}
