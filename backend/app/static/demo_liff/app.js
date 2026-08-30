const config = JSON.parse(document.querySelector("#liff-public-config").textContent);
const state = {
  accessToken: null,
  bootstrap: null,
};

const statusNode = document.querySelector("#status");
const editor = document.querySelector("#editor");
const rowsNode = document.querySelector("#rows");
const countNode = document.querySelector("#holding-count");
const addButton = document.querySelector("#add-row");
const dialog = document.querySelector("#preview-dialog");
const previewList = document.querySelector("#preview-list");
const disclosureRow = document.querySelector("#disclosure-row");
const disclosure = document.querySelector("#disclosure");
const confirmButton = document.querySelector("#confirm-save");

function setStatus(message, kind = "") {
  statusNode.textContent = message;
  statusNode.className = `status ${kind}`.trim();
}

function idempotencyKey(prefix) {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return `${prefix}-${[...bytes].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.accessToken) headers.Authorization = `Bearer ${state.accessToken}`;
  const response = await fetch(path, { ...options, headers, cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.error?.message || "目前無法完成操作，請稍後再試。");
  }
  return payload;
}

function options(selected = "") {
  const placeholder = '<option value="">請選擇</option>';
  return placeholder + state.bootstrap.universe.map(({ ticker, company }) => {
    const isSelected = ticker === selected ? " selected" : "";
    return `<option value="${ticker}"${isSelected}>${ticker} ${company}</option>`;
  }).join("");
}

function addRow(holding = null) {
  if (rowsNode.children.length >= state.bootstrap.max_holdings) return;
  const row = document.createElement("div");
  row.className = "holding-row";
  row.dataset.holdingId = holding?.id || "";
  row.dataset.version = holding?.version || "";
  row.innerHTML = `
    <label>股票<select class="ticker" required>${options(holding?.ticker)}</select></label>
    <label>股數<input class="shares" type="number" inputmode="decimal" min="0.0001" step="0.0001" value="${holding?.shares || ""}" required /></label>
    <label>平均成本<input class="cost" type="number" inputmode="decimal" min="0.0001" step="0.0001" value="${holding?.average_cost || ""}" required /></label>
    <button type="button" class="remove-row" aria-label="移除此列">×</button>`;
  row.querySelector(".remove-row").addEventListener("click", () => {
    row.remove();
    updateCount();
  });
  rowsNode.append(row);
  updateCount();
}

function updateCount() {
  const count = rowsNode.children.length;
  countNode.textContent = `${count} / ${state.bootstrap.max_holdings} 檔`;
  addButton.disabled = count >= state.bootstrap.max_holdings;
}

function collectRows() {
  const result = [...rowsNode.querySelectorAll(".holding-row")].map((row) => ({
    ticker: row.querySelector(".ticker").value,
    shares: row.querySelector(".shares").value,
    average_cost: row.querySelector(".cost").value,
    holding_id: row.dataset.holdingId || null,
    version: row.dataset.version ? Number(row.dataset.version) : null,
  }));
  for (const item of result) {
    if (!item.ticker || !item.shares || !item.average_cost) throw new Error("請完整填寫每一列。");
    if (!(Number(item.shares) > 0) || !(Number(item.average_cost) > 0)) {
      throw new Error("股數與平均成本必須大於 0。");
    }
  }
  const tickers = result.map((item) => item.ticker);
  if (new Set(tickers).size !== tickers.length) throw new Error("同一檔股票只能出現一次。");
  return result;
}

function showPreview() {
  try {
    const holdings = collectRows();
    previewList.replaceChildren();
    if (holdings.length === 0) {
      const empty = document.createElement("p");
      empty.textContent = "這會清空目前所有 Demo 持股。";
      previewList.append(empty);
    }
    for (const item of holdings) {
      const company = state.bootstrap.universe.find(({ ticker }) => ticker === item.ticker)?.company;
      const node = document.createElement("div");
      node.className = "preview-item";
      const identity = document.createElement("strong");
      identity.textContent = `${item.ticker} ${company}`;
      const values = document.createElement("span");
      values.textContent = `${item.shares} 股｜成本 ${item.average_cost}`;
      node.append(identity, values);
      previewList.append(node);
    }
    disclosureRow.hidden = state.bootstrap.disclosure_accepted;
    disclosure.checked = state.bootstrap.disclosure_accepted;
    dialog.showModal();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function savePortfolio() {
  if (!state.bootstrap.disclosure_accepted && !disclosure.checked) {
    setStatus("請先確認 Demo 資料使用說明。", "error");
    return;
  }
  confirmButton.disabled = true;
  try {
    if (!state.bootstrap.disclosure_accepted) {
      await api("/api/v1/demo/liff/disclosure", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey("liff-disclosure") },
      });
      state.bootstrap.disclosure_accepted = true;
    }
    const result = await api("/api/v1/demo/liff/portfolio", {
      method: "PUT",
      headers: { "Idempotency-Key": idempotencyKey("liff-portfolio") },
      body: JSON.stringify({
        expected_portfolio_version: state.bootstrap.portfolio.portfolio_version,
        holdings: collectRows(),
      }),
    });
    state.bootstrap.portfolio = result.portfolio;
    dialog.close();
    renderPortfolio();
    setStatus(`已安全儲存 ${result.portfolio.holdings.length} 檔 Demo 持股。`, "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    confirmButton.disabled = false;
  }
}

function renderPortfolio() {
  rowsNode.replaceChildren();
  for (const holding of state.bootstrap.portfolio.holdings) addRow(holding);
  if (state.bootstrap.portfolio.holdings.length === 0) addRow();
  updateCount();
  editor.hidden = false;
}

async function start() {
  try {
    if (!config.liffId) throw new Error("LIFF 尚未完成外部設定。");
    await liff.init({ liffId: config.liffId });
    if (!liff.isLoggedIn()) {
      liff.login({ redirectUri: window.location.href });
      return;
    }
    const idToken = liff.getIDToken();
    if (!idToken) throw new Error("無法取得 LINE 登入憑證，請由 LINE 內重新開啟。");
    const session = await api("/api/v1/demo/liff/session", {
      method: "POST",
      body: JSON.stringify({ id_token: idToken }),
    });
    state.accessToken = session.access_token;
    state.bootstrap = await api("/api/v1/demo/liff/bootstrap");
    renderPortfolio();
    setStatus("已載入你的 Demo Sandbox 持股。", "success");
  } catch (error) {
    setStatus(error.message || "目前無法開啟持股編輯器，請稍後再試。", "error");
  }
}

addButton.addEventListener("click", () => addRow());
document.querySelector("#preview").addEventListener("click", showPreview);
document.querySelector("#close").addEventListener("click", () => {
  if (window.liff?.isInClient()) liff.closeWindow();
});
confirmButton.addEventListener("click", savePortfolio);

start();
