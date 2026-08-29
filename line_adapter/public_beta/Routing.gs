function routeEntry_(raw) {
  var value = String(raw || "").trim();
  var routes = {
    "主選單": "MAIN_MENU",
    "menu": "MAIN_MENU",
    "📊 股票分析": "STOCK_ANALYSIS",
    "股票分析": "STOCK_ANALYSIS",
    "💼 持股健檢": "PORTFOLIO_HEALTH",
    "持股健檢": "PORTFOLIO_HEALTH",
    "➕ 新增持股": "ADD_HOLDING",
    "新增持股": "ADD_HOLDING",
    "📋 我的持股": "PORTFOLIO",
    "我的持股": "PORTFOLIO",
    "📰 金融情報": "FINANCIAL_INTELLIGENCE",
    "金融情報": "FINANCIAL_INTELLIGENCE",
    "⚙️ Demo 設定": "DEMO_SETTINGS",
    "Demo 設定": "DEMO_SETTINGS",
    "取消": "CANCEL",
    "DEMO_CANCEL": "CANCEL",
    "DEMO_DISCLOSURE_ACCEPT": "DISCLOSURE_ACCEPT|v1",
    "DEMO_ADD_CONFIRM": "ADD_CONFIRM",
    "DEMO_UPDATE_CONFIRM": "UPDATE_CONFIRM",
    "DEMO_DELETE_CONFIRM": "DELETE_CONFIRM",
    "DEMO_DELETE_MY_DATA": "DELETE_MY_DATA",
    "DEMO_DELETE_MY_DATA_CONFIRM": "DELETE_MY_DATA_CONFIRM"
  };
  if (routes[value]) return routes[value];
  if (/^DEMO_UPDATE\|[A-Za-z0-9-]{1,64}\|[0-9]+\|[0-9]{4}$/.test(value)) {
    return "UPDATE_SELECT|" + value.split("|").slice(1).join("|");
  }
  if (/^DEMO_DELETE\|[A-Za-z0-9-]{1,64}\|[0-9]+\|[0-9]{4}$/.test(value)) {
    return "DELETE_SELECT|" + value.split("|").slice(1).join("|");
  }
  return "CONVERSATION_INPUT";
}
