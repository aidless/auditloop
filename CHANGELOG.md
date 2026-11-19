# 变更记录

## [0.1.0] - 2026-11-19

首次公开发布（PyPI 分发名 `auditloop-oss`；import 名与 CLI 仍为 `auditloop`）。

### 包含

- **6 项确定性审计程序**：`bank_recon` / `ar_aging` / `revenue_cutoff` / `duplicate_payment` / `ar_sanity` / `ar_completeness`。
- **3 条分析性程序**：`revenue_vs_receivables` / `gross_margin_trend` / `cash_conversion`。
- **例外清单 + Excel 底稿**：demo 实跑 high 3 / medium 4 / low 3，退出码四档 0/1/2/3。
- **`scripts/check_readme.py`**：9 例自检，README 的程序表与 demo 计数从库对象真值重算（`cli.build_run()` + `inspect.getsource(analytics.run_all)`），不另抄清单。
- **85 项测试**，零依赖。
