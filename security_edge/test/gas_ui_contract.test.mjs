import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../..");
const context = { JSON, String, Number, RegExp };
vm.createContext(context);
for (const name of ["Routing.gs", "FlexBuilders.gs"]) {
  vm.runInContext(
    fs.readFileSync(path.join(root, "line_adapter/public_beta", name), "utf8"),
    context,
  );
}

test("six public-beta menu entries are present and distinct", () => {
  const menu = context.buildMainMenuFlex_();
  const buttons = menu.contents.footer.contents;
  assert.equal(buttons.length, 6);
  assert.deepEqual(
    [...buttons.map((button) => button.action.text)],
    ["📊 股票分析", "💼 持股健檢", "➕ 新增持股", "📋 我的持股", "📰 金融情報", "⚙️ Demo 設定"],
  );
  assert.equal(new Set(buttons.map((button) => context.routeEntry_(button.action.text))).size, 6);
});

test("Flex builders return LINE flex payloads and mutation previews require confirmation", () => {
  const preview = context.buildHoldingPreviewFlex_(
    "新增持股",
    { ticker: "2330", shares: 100, average_cost: 820 },
    "DEMO_ADD_CONFIRM",
  );
  assert.equal(preview.type, "flex");
  assert.equal(preview.contents.type, "bubble");
  assert.equal(preview.contents.footer.contents[0].action.data, "DEMO_ADD_CONFIRM");
  assert.equal(preview.contents.footer.contents[1].action.data, "DEMO_CANCEL");
});

test("routing preserves deterministic update/delete and cancellation commands", () => {
  assert.equal(context.routeEntry_("DEMO_ADD_CONFIRM"), "ADD_CONFIRM");
  assert.equal(
    context.routeEntry_("DEMO_UPDATE|holding-id|2|2330"),
    "UPDATE_SELECT|holding-id|2|2330",
  );
  assert.equal(
    context.routeEntry_("DEMO_DELETE|holding-id|2|2330"),
    "DELETE_SELECT|holding-id|2|2330",
  );
  assert.equal(context.routeEntry_("DEMO_CANCEL"), "CANCEL");
});
