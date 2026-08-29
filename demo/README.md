# F11 Streamlit Dashboard Demo

這個目錄提供 Financial AI Assistant 的受控作品集展示介面。預設模式只讀取固定、合成的
fixture，不發出網路請求；另一模式可連到同一台電腦上的 F10 FastAPI。

## 安裝與啟動

```bash
python -m pip install -e ".[dev,demo]"
python -m streamlit run demo/app.py
```

公開作品集 entrypoint 固定為零秘密、fixture-only：

```bash
python -m pip install -r demo/requirements.txt
python -m streamlit run demo/public_app.py
```

Public entrypoint 不顯示本機 FastAPI 選項，也不建立 API client。

若要測試本機 API 模式，請在另一個終端啟動：

```bash
uvicorn backend.app.main:app --reload
```

Dashboard 只接受帶有明確 port 的 `http://127.0.0.1`、`http://localhost` 或
`http://[::1]` origin，不接受外部網址、credentials、query 或 fragment。

## 展示邊界

- 離線分數由 frozen F7 artifact 對合成特徵產生，不是真實 2330 觀測，也不是績效證據。
- 中文 polarity 未通過驗證時維持 abstain；事件代理不是 sentiment ground truth。
- 不含真實持股、LINE token、API key、使用者資料或受限制資料集。
- F11/R1A 不呼叫外部 provider、FinBERT、LLM，也不修改 GAS。
- 畫面只呈現研究訊號，不預測漲跌，不構成投資建議，也不保證未來波動。
- F11B-2A current-market gate 只有 6/9 通過、exact features 只有 5/23；因此本頁不得描述為
  live current-market inference。

R1A 尚未取得公開 URL；部署步驟見 [Public Web Demo Release](../docs/public_web_demo_release.md)。
作品集截圖與完整說明見 [Portfolio Guide](../docs/portfolio_finalization.md)。
