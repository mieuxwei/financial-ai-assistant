function replyDemoMessage_(replyToken, message) {
  var token = requiredScriptProperty_("LINE_DEMO_CHANNEL_ACCESS_TOKEN");
  var response = UrlFetchApp.fetch("https://api.line.me/v2/bot/message/reply", {
    method: "post",
    contentType: "application/json",
    headers: { "Authorization": "Bearer " + token },
    payload: JSON.stringify({ replyToken: replyToken, messages: [message] }),
    muteHttpExceptions: true,
    followRedirects: false
  });
  var status = response.getResponseCode();
  console.log("line_reply_http_status=" + status);
  if (status < 200 || status >= 300) {
    var safeBody = String(response.getContentText() || "")
      .replace(/[A-Za-z0-9_\-]{80,}/g, "[redacted]")
      .slice(0, 300);
    console.error("LINE reply failed: HTTP " + status + " " + safeBody);
    throw new Error("LINE reply failed with HTTP " + status);
  }
}

function textMessage_(text) {
  return { type: "text", text: String(text).slice(0, 2000) };
}
