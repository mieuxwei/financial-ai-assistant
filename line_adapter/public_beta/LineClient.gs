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
  if (response.getResponseCode() < 200 || response.getResponseCode() >= 300) {
    throw new Error("LINE reply failed");
  }
}

function textMessage_(text) {
  return { type: "text", text: String(text).slice(0, 2000) };
}
