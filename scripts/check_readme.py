#!/usr/bin/env python3
"""核对 README 里那些"能跑出来的数字"是否与本仓代码一致。

auditloop 的 README 首屏是六项审计程序表、三条分析性程序表与一段真实 demo 输出
（6 行例外计数、high 3 条、medium/low 7 条）。这类数字最典型的腐化方式是改完
fixture 忘了改 README：文档说 high 3，demo 实际 4，读者照着写底稿就错了。

只核对**可复算**的项：程序清单、分析性程序清单、demo 计数与严重度、退出码档数。
不核对叙述性判断与已知边界（那些是设计说明，不是数）。

退出码：0 = 全部一致；1 = 有不一致；2 = 用法错/导入失败。
"""

from __future__ import annotations

import argparse
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT
sys.path.insert(0, str(SRC))

# README 的 demo 摘要表：| bank_recon | 存在性 | ok | 4 |
DEMO_ROW = re.compile(
    r"^\| (bank_recon|ar_aging|revenue_cutoff|duplicate_payment|ar_sanity|ar_completeness) "
    r"\| [^|]+ \| ok \| (\d+) \|", re.M
)
PROGRAM_ROW = re.compile(r"^\| `(\w+)` [^|]*\| [^|]+ \| [^|]+ \|", re.M)
ANALYTIC_ROW = re.compile(r"^\| `(\w+)` \| [^|]+ \|", re.M)
EXIT_ROW = re.compile(r"^\| (\d) \| [^|]+ \|", re.M)


def actual() -> dict:
    from auditloop import analytics, cli

    run = cli.build_run()

    # 三条分析性程序：从 run_all 的源码里取实际调用的函数名，不另写一份清单
    src = inspect.getsource(analytics.run_all)
    m = re.search(r"for fn in \(([^)]*)\)", src)
    analytic_names = [x.strip() for x in m.group(1).split(",")] if m else []

    sev: dict[str, int] = {}
    for f in run.findings:
        sev[f.severity] = sev.get(f.severity, 0) + 1

    return {
        "programs": [s.name for s in run.steps],
        "analytics": analytic_names,
        "by_check": run.by_check(),
        "high": len(run.high),
        "medium": sev.get("medium", 0),
        "low": sev.get("low", 0),
        "total": len(run.findings),
        "status": run.status,
    }


def _section(text: str, heading: str) -> str:
    """只取某一节，避免其它表格长得像被一起扫进去。"""
    i = text.find(heading)
    if i < 0:
        return ""
    j = text.find("\n## ", i + 1)
    return text[i:] if j < 0 else text[i:j]


def compare(text: str, got: dict) -> list[str]:
    problems: list[str] = []

    # 六项审计程序表：程序名集合必须与 build_run 注册的一致
    six = _section(text, "## 六项审计程序")
    names = PROGRAM_ROW.findall(six)
    if set(names) != set(got["programs"]) or len(names) != len(got["programs"]):
        problems.append(
            f"六项程序表：README 写 {sorted(names)}，实测 {sorted(got['programs'])}"
        )

    # 三条分析性程序表
    three = _section(text, "## 分析性程序")
    names3 = ANALYTIC_ROW.findall(three)
    if set(names3) != set(got["analytics"]) or len(names3) != len(got["analytics"]):
        problems.append(
            f"分析性程序表：README 写 {sorted(names3)}，实测 {sorted(got['analytics'])}"
        )

    # demo 摘要表的 6 行计数
    demo = _section(text, "## 演示输出")
    rows = {name: int(n) for name, n in DEMO_ROW.findall(demo)}
    if rows != got["by_check"]:
        problems.append(f"demo 例外计数：README 写 {rows}，实测 {got['by_check']}")

    # high / medium+low
    m = re.search(r"high 例外 (\d+) 条", text)
    if not m:
        problems.append("找不到「high 例外 N 条」")
    elif int(m.group(1)) != got["high"]:
        problems.append(f"high 例外：README 写 {m.group(1)}，实测 {got['high']}")

    m = re.search(r"完整输出另含 medium/low (\d+) 条", text)
    if not m:
        problems.append("找不到「medium/low N 条」")
    elif int(m.group(1)) != got["medium"] + got["low"]:
        problems.append(
            f"medium/low 例外：README 写 {m.group(1)}，"
            f"实测 medium {got['medium']} + low {got['low']} = {got['medium'] + got['low']}"
        )

    # 退出码四档 0/1/2/3
    exit_sec = _section(text, "`auditloop analytics` 的退出码")
    codes = sorted(int(x) for x in EXIT_ROW.findall(exit_sec))
    if codes != [0, 1, 2, 3]:
        problems.append(f"退出码档位：README 写 {codes}，应为 [0, 1, 2, 3]")

    return problems


def _selftest() -> int:
    got = {
        "programs": ["bank_recon", "ar_aging", "revenue_cutoff",
                     "duplicate_payment", "ar_sanity", "ar_completeness"],
        "analytics": ["revenue_vs_receivables", "gross_margin_trend", "cash_conversion"],
        "by_check": {"bank_recon": 4, "ar_aging": 1, "revenue_cutoff": 2,
                     "duplicate_payment": 1, "ar_sanity": 1, "ar_completeness": 1},
        "high": 3, "medium": 4, "low": 3, "total": 10, "status": "attention_required",
    }
    good = (
        "`auditloop analytics` 的退出码：\n\n"
        "| 码 | 含义 |\n| ---: | --- |\n"
        "| 0 | 跑完，没问题 |\n| 1 | 跑完，有异常 |\n"
        "| 2 | 没跑成 |\n| 3 | 跑完了但一条都没判定 |\n\n"
        "## 六项审计程序（判据各一句）\n\n"
        "| 程序 | 认定 | 判据 |\n| --- | --- | --- |\n"
        "| `bank_recon` 银行余额调节 | 存在性 | x |\n"
        "| `ar_aging` 应收账龄 | 计价 | x |\n"
        "| `revenue_cutoff` 收入截止 | 截止 | x |\n"
        "| `duplicate_payment` 重复付款 | 存在性 | x |\n"
        "| `ar_sanity` 应收异常 | 计价 | x |\n"
        "| `ar_completeness` 应收完整性 | 完整性 | x |\n\n"
        "## 分析性程序（三条比率/趋势）\n\n"
        "| 程序 | 触发条件 |\n| --- | --- |\n"
        "| `revenue_vs_receivables` | x |\n"
        "| `gross_margin_trend` | x |\n"
        "| `cash_conversion` | x |\n\n"
        "## 演示输出（真实运行）\n\n"
        "- 结论：**attention_required**（high 例外 3 条）\n\n"
        "| 程序 | 认定 | 状态 | 例外 |\n| --- | --- | --- | ---: |\n"
        "| bank_recon | 存在性 | ok | 4 |\n"
        "| ar_aging | 计价 | ok | 1 |\n"
        "| revenue_cutoff | 截止 | ok | 2 |\n"
        "| duplicate_payment | 存在性 | ok | 1 |\n"
        "| ar_sanity | 计价 | ok | 1 |\n"
        "| ar_completeness | 完整性 | ok | 1 |\n\n"
        "例外清单（节选，`auditloop demo` 的完整输出另含 medium/low 7 条）：\n"
    )
    cases: list[tuple[str, str, bool, str]] = [
        ("干净文本", good, False, "合规输入必须放行"),
        ("六项程序少一项", good.replace("| `ar_sanity` 应收异常 | 计价 | x |\n", ""), True,
         "程序清单漂移必须报"),
        ("分析程序改名", good.replace("`cash_conversion`", "`cash_conv2`"), True,
         "分析程序清单漂移必须报"),
        ("demo 计数漂移", good.replace("| bank_recon | 存在性 | ok | 4 |",
                                    "| bank_recon | 存在性 | ok | 5 |"), True,
         "demo 例外计数漂移必须报"),
        ("high 漂移", good.replace("high 例外 3 条", "high 例外 4 条"), True,
         "high 计数漂移必须报"),
        ("medium/low 漂移", good.replace("medium/low 7 条", "medium/low 8 条"), True,
         "medium/low 计数漂移必须报"),
        ("退出码少一档", good.replace("| 3 | 跑完了但一条都没判定 |\n", ""), True,
         "退出码档位漂移必须报"),
        ("别的表长得像", good.replace("## 六项审计程序",
                                  "| 无关 | 99 / 100 |\n\n## 六项审计程序"), False,
         "不相关表格不得污染判定"),
    ]
    fails: list[str] = []
    for name, text, expect_bad, why in cases:
        problems = compare(text, got)
        if bool(problems) != expect_bad:
            fails.append(f"{name}（期望{'红' if expect_bad else '绿'}，实际 {problems or '绿'}；{why}）")
        else:
            print(f"  ✓ {name}：{'红了' if expect_bad else '放行'} —— {why}")

    real = compare((ROOT / "README.md").read_text(), actual())
    if real:
        fails.append(f"真实 README 与实测不一致：{real[:3]}")
    else:
        print("  ✓ 真实 README：程序清单/分析程序/demo 计数/严重度/退出码全部重算一致")

    if fails:
        print(f"\n✗ selftest {len(fails)} 条不通过：")
        for f in fails:
            print("  " + f)
        return 1
    red = len([c for c in cases if c[2]])
    green = len([c for c in cases if not c[2]]) + 1
    print(f"\n✓ selftest 全通过（{red + green} 例：{red} 条必红 + {green} 条必绿）")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="核对 README 数字是否与本仓代码一致")
    ap.add_argument("--selftest", action="store_true", help="非空性反证自测")
    ap.add_argument("--readme", default=str(ROOT / "README.md"))
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()
    got = actual()
    print("实测：" + str({k: v for k, v in got.items() if k != "by_check"}))
    print("by_check=" + str(got["by_check"]))
    problems = compare(Path(args.readme).read_text(), got)
    if problems:
        print("\nREADME 与代码不一致：")
        for p in problems:
            print("  ✗ " + p)
        return 1
    print("README 数字全部可复算。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
