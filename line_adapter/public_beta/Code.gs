/** Public-safe Demo GAS entrypoint. Never deploy this source to the private Apps Script project. */
function doPost(e) {
  var envelope;
  try {
    var request = JSON.parse(e.postData.contents || "{}");
    envelope = verifyEdgeEnvelope_(request);
  } catch (securityError) {
    return jsonStatus_("rejected");
  }
  try {
    var message = dispatchDemoEvent_(envelope);
    if (message && envelope.reply_token) {
      replyDemoMessage_(envelope.reply_token, message);
    }
    return jsonStatus_("ok");
  } catch (applicationError) {
    if (envelope.reply_token) {
      try {
        replyDemoMessage_(
          envelope.reply_token,
          textMessage_("目前無法完成操作，請稍後再試，或輸入「主選單」重新開始。")
        );
        return jsonStatus_("ok");
      } catch (replyError) {
        return jsonStatus_("rejected");
      }
    }
    return jsonStatus_("ok");
  }
}

function jsonStatus_(status) {
  return ContentService.createTextOutput(JSON.stringify({ status: status }))
    .setMimeType(ContentService.MimeType.JSON);
}

function dispatchDemoEvent_(envelope) {
  enforceDemoRateLimit_(envelope.demo_principal_id);
  if (envelope.message.type === "follow") return buildMainMenuFlex_();
  var principalId = envelope.demo_principal_id;
  var value = envelope.message.type === "postback"
    ? envelope.message.data
    : String(envelope.message.text || "").trim();
  var route = routeEntry_(value);
  var state = getDemoState_(principalId);

  if (route === "CANCEL") {
    clearDemoState_(principalId);
    return textMessage_("已取消目前操作。");
  }
  if (route === "MAIN_MENU") return buildMainMenuFlex_();
  if (route === "ADD_HOLDING") return beginAddHolding_(principalId);
  if (route === "PORTFOLIO") return buildPortfolioListFlex_(getPortfolio_(principalId));
  if (route === "PORTFOLIO_HEALTH") {
    return buildPortfolioHealthFlex_(backendRequest_(principalId, "POST", "/portfolio/health"));
  }
  if (route === "STOCK_ANALYSIS") {
    setDemoState_(principalId, { step: "STOCK_ANALYSIS_WAITING_TICKER" });
    return textMessage_("請輸入 frozen universe 內的四碼股票代號，例如 2330。");
  }
  if (route === "FINANCIAL_INTELLIGENCE") {
    setDemoState_(principalId, { step: "INTELLIGENCE_WAITING_TICKER" });
    return textMessage_("請輸入要查看金融情報的四碼股票代號，例如 2330。");
  }
  if (route === "DEMO_SETTINGS") return buildDemoSettingsFlex_();
  if (route.indexOf("DISCLOSURE_ACCEPT|") === 0) {
    backendRequest_(principalId, "POST", "/me/disclosure", null, envelope.event_id);
    setDemoState_(principalId, { step: "ADD_WAITING_TICKER" });
    return textMessage_("請輸入要新增的四碼股票代號。");
  }
  if (route.indexOf("UPDATE_SELECT|") === 0) return beginUpdateHolding_(principalId, route);
  if (route.indexOf("DELETE_SELECT|") === 0) return beginDeleteHolding_(principalId, route);
  if (route === "DELETE_MY_DATA") return buildDeleteMyDataConfirmFlex_();
  if (route === "DELETE_MY_DATA_CONFIRM") {
    backendRequest_(principalId, "DELETE", "/me");
    clearDemoState_(principalId);
    return textMessage_("你的 Demo Sandbox 持股與設定已刪除。");
  }
  if (route === "ADD_CONFIRM") return confirmAddHolding_(envelope, state);
  if (route === "UPDATE_CONFIRM") return confirmUpdateHolding_(envelope, state);
  if (route === "DELETE_CONFIRM") return confirmDeleteHolding_(envelope, state);
  return continueDemoConversation_(envelope, state, value);
}

function beginAddHolding_(principalId) {
  var me = backendRequest_(principalId, "GET", "/me");
  if (!me.disclosure_accepted) {
    setDemoState_(principalId, { step: "DISCLOSURE_PENDING" });
    return buildDisclosureFlex_();
  }
  setDemoState_(principalId, { step: "ADD_WAITING_TICKER" });
  return textMessage_("請輸入要新增的四碼股票代號。");
}

function continueDemoConversation_(envelope, state, value) {
  var principalId = envelope.demo_principal_id;
  if (!state) return textMessage_("請使用主選單開始操作。輸入「主選單」可再次開啟。");
  if (state.step === "STOCK_ANALYSIS_WAITING_TICKER") {
    var analysisTicker = requireTicker_(value);
    clearDemoState_(principalId);
    return buildStockAnalysisFlex_(
      backendRequest_(principalId, "GET", "/research/stock-analysis/" + analysisTicker)
    );
  }
  if (state.step === "INTELLIGENCE_WAITING_TICKER") {
    var intelligenceTicker = requireTicker_(value);
    clearDemoState_(principalId);
    return buildFinancialIntelligenceFlex_(
      backendRequest_(principalId, "GET", "/research/intelligence/" + intelligenceTicker)
    );
  }
  if (state.step === "ADD_WAITING_TICKER") {
    state.ticker = requireTicker_(value);
    backendRequest_(principalId, "GET", "/research/stock-analysis/" + state.ticker);
    state.step = "ADD_WAITING_SHARES";
    setDemoState_(principalId, state);
    return textMessage_("請輸入持有股數。");
  }
  if (state.step === "ADD_WAITING_SHARES") {
    state.shares = requirePositiveNumber_(value, 10000000);
    state.step = "ADD_WAITING_COST";
    setDemoState_(principalId, state);
    return textMessage_("請輸入平均成本。");
  }
  if (state.step === "ADD_WAITING_COST") {
    state.average_cost = requirePositiveNumber_(value, 1000000);
    state.step = "ADD_CONFIRM";
    setDemoState_(principalId, state);
    return buildHoldingPreviewFlex_("新增持股", state, "DEMO_ADD_CONFIRM");
  }
  if (state.step === "UPDATE_WAITING_SHARES") {
    state.shares = requirePositiveNumber_(value, 10000000);
    state.step = "UPDATE_WAITING_COST";
    setDemoState_(principalId, state);
    return textMessage_("請輸入新的平均成本。");
  }
  if (state.step === "UPDATE_WAITING_COST") {
    state.average_cost = requirePositiveNumber_(value, 1000000);
    state.step = "UPDATE_CONFIRM";
    setDemoState_(principalId, state);
    return buildHoldingPreviewFlex_("修改持股", state, "DEMO_UPDATE_CONFIRM");
  }
  return textMessage_("目前操作已逾時或輸入無效，請從主選單重新開始。");
}

function confirmAddHolding_(envelope, state) {
  requireState_(state, "ADD_CONFIRM");
  var result = backendRequest_(
    envelope.demo_principal_id,
    "POST",
    "/portfolio/holdings",
    { ticker: state.ticker, shares: state.shares, average_cost: state.average_cost },
    envelope.event_id
  );
  clearDemoState_(envelope.demo_principal_id);
  return textMessage_("Demo 持股新增完成：" + result.holding.ticker + "。");
}

function beginUpdateHolding_(principalId, route) {
  var parts = route.split("|");
  setDemoState_(principalId, {
    step: "UPDATE_WAITING_SHARES",
    holding_id: parts[1],
    version: Number(parts[2]),
    ticker: parts[3]
  });
  return textMessage_("請輸入新的持有股數。");
}

function confirmUpdateHolding_(envelope, state) {
  requireState_(state, "UPDATE_CONFIRM");
  backendRequest_(
    envelope.demo_principal_id,
    "PATCH",
    "/portfolio/holdings/" + encodeURIComponent(state.holding_id),
    { shares: state.shares, average_cost: state.average_cost, version: state.version },
    envelope.event_id
  );
  clearDemoState_(envelope.demo_principal_id);
  return textMessage_("Demo 持股修改完成。");
}

function beginDeleteHolding_(principalId, route) {
  var parts = route.split("|");
  var state = {
    step: "DELETE_CONFIRM",
    holding_id: parts[1],
    version: Number(parts[2]),
    ticker: parts[3]
  };
  setDemoState_(principalId, state);
  return buildHoldingPreviewFlex_("刪除持股", state, "DEMO_DELETE_CONFIRM");
}

function confirmDeleteHolding_(envelope, state) {
  requireState_(state, "DELETE_CONFIRM");
  backendRequest_(
    envelope.demo_principal_id,
    "DELETE",
    "/portfolio/holdings/" + encodeURIComponent(state.holding_id) + "?version=" + state.version,
    null,
    envelope.event_id
  );
  clearDemoState_(envelope.demo_principal_id);
  return textMessage_("Demo 持股已刪除。");
}

function getPortfolio_(principalId) {
  return backendRequest_(principalId, "GET", "/portfolio");
}

function requireState_(state, expected) {
  if (!state || state.step !== expected) throw new Error("invalid state");
}

function requireTicker_(value) {
  if (!/^[0-9]{4}$/.test(value)) throw new Error("invalid ticker");
  return value;
}

function requirePositiveNumber_(value, ceiling) {
  var parsed = Number(value);
  if (!isFinite(parsed) || parsed <= 0 || parsed > ceiling) throw new Error("invalid number");
  return parsed;
}
