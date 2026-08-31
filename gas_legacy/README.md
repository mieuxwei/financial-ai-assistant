# GAS Legacy

舊 GAS 是私人原型。因舊程式曾包含私人設定，所以不直接複製到公開 repository。

未來只會加入經過清理、沒有秘密的 LINE adapter。此目錄不得放入舊 token、Sheet ID 或真實使用者資料。

R0 的原始備份與 migration copy 只存在 Git 忽略的私有 `.tools/` 路徑，不屬於此公開目錄。
後續 F11B 只能在 verified migration copy 上作 additive、可回復的整合；不得覆蓋 sole original、
提交私人 GAS source 或先遷移持股寫入。詳見
`docs/internal/gas_migration_safety_freeze.md`。
