function buildMainMenuFlex_() {
  return flexMessage_("Financial AI Assistant Public Beta", bubble_(
    "Financial AI Assistant",
    [
      textBox_("作品集公測／研究展示", "#0F766E", "bold"),
      textBox_("Demo Sandbox 不連接券商、私人持股或即時市場推論。", "#4B5563", "regular")
    ],
    [
      menuButton_("📊 股票分析", "📊 股票分析"),
      menuButton_("💼 持股健檢", "💼 持股健檢"),
      menuButton_("➕ 新增持股", "➕ 新增持股"),
      menuButton_("📋 我的持股", "📋 我的持股"),
      menuButton_("📰 金融情報", "📰 金融情報"),
      menuButton_("⚙️ Demo 設定", "⚙️ Demo 設定")
    ]
  ));
}

function buildDisclosureFlex_() {
  return flexMessage_("Demo 資料使用說明", bubble_(
    "使用前說明",
    [
      textBox_(
        "此為作品集公測版。輸入的持股資料僅用於 Demo Sandbox，請勿輸入帳號、身分資料或其他敏感資訊。",
        "#374151",
        "regular"
      ),
      textBox_("Demo 持股預計最長保存 30 天，亦可隨時自行刪除。", "#374151", "regular")
    ],
    [postbackButton_("同意並繼續", "DEMO_DISCLOSURE_ACCEPT"), postbackButton_("取消", "DEMO_CANCEL")]
  ));
}

function buildHoldingPreviewFlex_(title, state, confirmData) {
  var rows = [keyValueRow_("股票代號", state.ticker || "—")];
  if (state.shares !== undefined) rows.push(keyValueRow_("持有股數", String(state.shares)));
  if (state.average_cost !== undefined) rows.push(keyValueRow_("平均成本", String(state.average_cost)));
  return flexMessage_(title + "確認", bubble_(
    title + "預覽",
    rows.concat([textBox_("確認後才會寫入 Demo Sandbox。", "#B45309", "regular")]),
    [postbackButton_("✅ 確認", confirmData), postbackButton_("❌ 取消", "DEMO_CANCEL")]
  ));
}

function buildPortfolioListFlex_(portfolio) {
  var body = [
    textBox_("DEMO SANDBOX PORTFOLIO", "#0F766E", "bold"),
    textBox_("不含即時價格與未實現損益。", "#4B5563", "regular")
  ];
  var footer = [menuButton_("新增持股", "➕ 新增持股")];
  if (!portfolio.holdings.length) body.push(textBox_("目前沒有 Demo 持股。", "#374151", "regular"));
  portfolio.holdings.forEach(function(holding) {
    body.push(separator_());
    body.push(textBox_(holding.ticker + " " + holding.company, "#111827", "bold"));
    body.push(keyValueRow_("股數", String(holding.shares)));
    body.push(keyValueRow_("平均成本", String(holding.average_cost)));
    footer.push(postbackButton_(
      "修改 " + holding.ticker,
      "DEMO_UPDATE|" + holding.id + "|" + holding.version + "|" + holding.ticker
    ));
    footer.push(postbackButton_(
      "刪除 " + holding.ticker,
      "DEMO_DELETE|" + holding.id + "|" + holding.version + "|" + holding.ticker
    ));
  });
  return flexMessage_("我的 Demo 持股", bubble_("我的持股", body, footer));
}

function buildPortfolioHealthFlex_(health) {
  var body = [
    textBox_("CONTROLLED RESEARCH SIGNAL", "#0F766E", "bold"),
    textBox_("不使用即時價格，因此不計算 ROI。", "#4B5563", "regular")
  ];
  if (!health.items.length) body.push(textBox_("請先新增 Demo 持股。", "#374151", "regular"));
  health.items.forEach(function(item) {
    body.push(separator_());
    body.push(textBox_(item.holding.ticker + " " + item.holding.company, "#111827", "bold"));
    body.push(keyValueRow_("股數", String(item.holding.shares)));
    body.push(keyValueRow_("平均成本", String(item.holding.average_cost)));
    if (item.research.status === "CONTROLLED_RESEARCH_SIGNAL") {
      body.push(keyValueRow_("受控研究風險", item.research.communication_band));
      body.push(keyValueRow_("歷史百分位", item.research.historical_percentile.toFixed(1) + "%"));
    } else {
      body.push(keyValueRow_("受控研究訊號", "此 ticker 暫無 fixture"));
    }
    if (item.intelligence.market_reaction_magnitude) {
      body.push(keyValueRow_("市場反應幅度", item.intelligence.market_reaction_magnitude));
    }
  });
  body.push(textBox_(health.limitation, "#6B7280", "regular"));
  return flexMessage_("Demo 持股健檢", bubble_("持股健檢", body, [menuButton_("回主選單", "主選單")]));
}

function buildStockAnalysisFlex_(analysis) {
  var body = [
    textBox_("CONTROLLED RESEARCH SIGNAL", "#0F766E", "bold"),
    textBox_(analysis.ticker + " " + analysis.company, "#111827", "bold")
  ];
  if (analysis.research.status === "CONTROLLED_RESEARCH_SIGNAL") {
    body.push(keyValueRow_("相對波動異常分數", analysis.research.score.toFixed(2) + "×"));
    body.push(keyValueRow_("歷史百分位", analysis.research.historical_percentile.toFixed(1) + "%"));
    body.push(keyValueRow_("溝通分級", analysis.research.communication_band));
  } else {
    body.push(textBox_("此 ticker 目前沒有公開受控 fixture；不會產生假分數。", "#B45309", "regular"));
  }
  body.push(textBox_(analysis.limitation, "#6B7280", "regular"));
  return flexMessage_("股票分析", bubble_("股票分析", body, [menuButton_("金融情報", "📰 金融情報")]));
}

function buildFinancialIntelligenceFlex_(response) {
  var intelligence = response.intelligence;
  var body = [
    textBox_(response.ticker + " " + response.company, "#111827", "bold"),
    textBox_("受控金融情報", "#0F766E", "bold")
  ];
  if (intelligence.status === "CONTROLLED_RESEARCH_INTELLIGENCE") {
    body.push(keyValueRow_("事件分類", intelligence.event_class || "未分類"));
    body.push(textBox_(intelligence.event_summary || "受控事件摘要", "#374151", "regular"));
    body.push(keyValueRow_("市場反應幅度", intelligence.market_reaction_magnitude || "未提供"));
  } else {
    body.push(textBox_("此 ticker 目前沒有公開受控情報 fixture。", "#B45309", "regular"));
  }
  body.push(textBox_(intelligence.chinese_sentiment_message, "#6B7280", "regular"));
  body.push(textBox_(response.limitation, "#6B7280", "regular"));
  return flexMessage_("金融情報", bubble_("金融情報", body, [menuButton_("回主選單", "主選單")]));
}

function buildDemoSettingsFlex_() {
  return flexMessage_("Demo 設定", bubble_(
    "Demo 設定",
    [
      textBox_("持股資料最長保存 30 天，可隨時刪除。", "#374151", "regular"),
      textBox_("即時市場推論尚未啟用（F11B-2 維持 blocked）。", "#374151", "regular"),
      textBox_("中文文字情緒目前尚未通過獨立驗證。", "#374151", "regular"),
      textBox_("📷 截圖匯入 — Public Beta 尚未開放", "#6B7280", "regular")
    ],
    [
      postbackButton_("刪除我的 Demo 資料", "DEMO_DELETE_MY_DATA"),
      menuButton_("回主選單", "主選單")
    ]
  ));
}

function buildDeleteMyDataConfirmFlex_() {
  return flexMessage_("刪除 Demo 資料確認", bubble_(
    "確認刪除",
    [textBox_("將刪除你的全部 Demo 持股、設定與暫存狀態。此操作不影響私人 LINE OA。", "#B91C1C", "regular")],
    [postbackButton_("確認刪除", "DEMO_DELETE_MY_DATA_CONFIRM"), postbackButton_("取消", "DEMO_CANCEL")]
  ));
}

function buildLimitationFlex_() {
  return flexMessage_("研究限制", bubble_(
    "研究限制",
    [
      textBox_("這是 Controlled Research Demo，不是即時交易系統。", "#374151", "regular"),
      textBox_("此模型不預測股價上漲或下跌。", "#374151", "regular"),
      textBox_("研究訊號不構成投資建議。", "#374151", "regular")
    ],
    [menuButton_("回主選單", "主選單")]
  ));
}

function flexMessage_(altText, contents) {
  return { type: "flex", altText: altText.slice(0, 400), contents: contents };
}

function bubble_(title, bodyContents, footerContents) {
  return {
    type: "bubble",
    header: { type: "box", layout: "vertical", contents: [textBox_(title, "#111827", "bold")] },
    body: { type: "box", layout: "vertical", spacing: "md", contents: bodyContents },
    footer: { type: "box", layout: "vertical", spacing: "sm", contents: footerContents }
  };
}

function textBox_(text, color, weight) {
  return { type: "text", text: String(text), wrap: true, color: color, weight: weight, size: "sm" };
}

function keyValueRow_(key, value) {
  return {
    type: "box",
    layout: "horizontal",
    contents: [
      { type: "text", text: key, size: "sm", color: "#6B7280", flex: 2 },
      { type: "text", text: String(value), size: "sm", color: "#111827", align: "end", wrap: true, flex: 3 }
    ]
  };
}

function menuButton_(label, text) {
  return {
    type: "button",
    style: "secondary",
    height: "sm",
    action: { type: "message", label: label, text: text }
  };
}

function postbackButton_(label, data) {
  return {
    type: "button",
    style: "primary",
    height: "sm",
    action: { type: "postback", label: label, data: data, displayText: label }
  };
}

function separator_() {
  return { type: "separator", margin: "md" };
}
