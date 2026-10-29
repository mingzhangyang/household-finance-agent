# 交接说明：官方原文复核与 M2 第一项“按年份管理规则”（2026-10-29）

供评审人、项目负责人或下一位接手的工程师（或代理）使用。接续[上一份交接说明](handover-2026-10-29.md)（PR #10，已合并为 `02c3a50`）。所有数据均为虚构示例。

## 1. 当前状态

| 项目 | 状态 |
|---|---|
| 分支 | `claude/gracious-bohr-kv7c41`，基于 `main` 的 `02c3a50` |
| PR | 尚未创建（项目负责人决定是否开 PR；`claude/*` 分支推送不触发 GitHub Actions，开 PR 后才会运行） |
| 计算引擎数值 | 不变。新增每年的规则依据标签；输出契约升为 1.1 |
| 本地验证 | 全部通过（第 4 节） |
| 阶段门槛 | 工程补充；M0 范围签署、专业复核仍未完成。M0 决策记录为草案，等待负责人确认 |

## 2. 改动内容

| 提交 | 内容 |
|---|---|
| 官方原文复核 | 直接下载并阅读 IRS 文件、Pub. L. 119-21、SSA 在 Federal Register 上的 2026/2027 年公告、T.D. 9930/10001 和 20 CFR 条文，逐项核对规则登记表，**未发现不一致**；记录文件哈希与定位（[原文复核记录](primary-source-review-2026-10-29.md)）。登记表改引 Federal Register 和 CFR 原文；修正社保一行把 Example 3 写成已测试的错误。新增 Rev. Proc. 2025-32 印刷税表的 12 个已知答案和 Pub 915 Example 3，并让验证器的税表副本也接受这些已知答案检查 |
| M2：按年份管理规则 | `tax2026.py` 按税年登记已公布数值（所得税表 2026；社保工资上限 2026–2027；401(k) 基本限额 2026）；没有已公布数值的年份以最近一个已公布年份为基础按假设年率推算，并标为 `projected`。每行新增 `rule_basis`；`tax.tax_law_year` 为所用已公布年份，`tax.policy` 逐年书写；验证器有独立的录入副本并逐项核对；报告年度审计新增“本年度规则依据” |
| M0 决策记录草案 | [m0-scope-decision.md](m0-scope-decision.md)：把 ROADMAP §7 的五项决定整理成选项、当前基线、影响和工程建议，留给负责人确认 |

## 3. 如何复现

```sh
sh scripts/verify_local.sh
python scripts/verify_m1_cases.py --output /tmp/m1-differences.json
python -m unittest tests.test_rule_years tests.test_golden -v
HFA_VERIFIER_FUZZ_PLANS=500 HFA_VERIFIER_FUZZ_SEED=7 python -m unittest discover -s tests -p test_verifier_independence.py -k test_valid_outputs
# 真实浏览器与证据包
npm ci --ignore-scripts
sudo apt-get update && sudo apt-get install -y fonts-noto-cjk
HFA_BROWSER_EXECUTABLE=/opt/pw-browsers/chromium python scripts/collect_evidence.py --output /tmp/finance-evidence --browser
```

原文复核所用文件可按[原文复核记录](primary-source-review-2026-10-29.md)中的网址重新下载，并用记录的 SHA256 确认是同一版本（IRS 网页本身不保证字节稳定，只对固定文件记录了哈希）。

## 4. 证据（本地结果）

- `verify_local.sh`：208 个测试通过；40 年 / 300 路径示例的验证断言 6,015 条（此前 5,895 条，新增的是每年三类规则依据的检查）；同引擎重放通过；第 17 条路径独立核对通过（6,030 条断言）。
- `verify_m1_cases.py`：4 个案例、11 年、599 项比较全部通过（数值未变）。
- 数值不变的直接证据：用改动前后的引擎分别运行示例方案、4 个 M1 案例和 4 个高工资变体（假设指数 0%、2.5%、10%，覆盖推算的工资上限和 401(k) 限额），除新增标签和元数据外逐字段完全相同；一个超限方案在两版中以相同信息被拒绝。
- 随机抽样（种子 7、8，各 500 个方案）：973 个有效结果和 3,892 条追踪路径全部通过；33,249 次单字段篡改全部被拒绝（规则依据的指数改动 1e-6 即被拒绝）。
- 已知答案：改动引擎或验证器税表中的任一税阶上限或税率，原文印刷行的测试都会失败（已逐项试验）。
- 真实 Chromium（Playwright 1.56.1，预装 Chromium 153.0.8010.12，Noto Sans CJK SC）：44 项检查通过，比此前多 8 项“推算年份被改标为已公布时报告必须拒绝显示”的错误状态；桌面与手机视口逐年核对规则依据文字。
- 准确提交上的 `collect_evidence.py --browser` 结果记录在本分支对应的会话/PR 说明中。

## 5. 行为与兼容性变化

- **输出**：每行新增 `rule_basis`（`income_tax_tables`、`oasdi_wage_base`、`elective_deferral_limit` 各含 `status`、`base_year`、`multiplier`、`source_id`）。`tax.policy` 改为逐年文字，例如 `2026 published federal tables indexed hypothetically to 2028; NOT published 2028 law`。`evidence_status.contract_version` 为 `1.1`，`tax_rules` 为 `published_tax_year_rules_with_labeled_hypothetical_projection`。`rule_scope` 第一条由登记表生成。`rules_sources` 中社保工资上限和 401(k) 限额改引 Federal Register 公告和 Notice 2025-67。
- **引擎指纹**：`audit_plan.py`、`tax2026.py` 有改动，`engine_source_sha256` 随之变化；旧报告应重新生成。
- **验证器**：含 `evidence_status` 的结果和所有 trace 必须带 `rule_basis`，且须与验证器的录入副本完全一致；`tax_law_year` 必须是整数。没有任何证据元数据的旧格式结果仍可验证，但数值仍按同一登记表核对。
- **报告**：年度审计新增“本年度规则依据”；规则依据缺失、格式错误，或把推算年份标为已公布时，隐藏结论并禁用导出。
- **API**：`payroll_tax(wages, status, year, assumed_rate)` 取代原来的 `wage_base_multiplier` 参数（仓库内只有引擎调用）。

## 6. 评审重点与设计说明

- **两份登记表**：引擎（`tax2026.PUBLISHED_*`）与验证器（`verify_outputs.PUBLISHED_INCOME_TAX`、`OASDI_WAGE_BASE`、`ELECTIVE_DEFERRAL`、`RULE_SOURCES`）分别录入。只改一份会导致验证失败（`tests/test_rule_years.py` 有意演示）。
- **报告模板的已公布年份列表**：`assets/audit-template.html` 的 `publishedRuleYears()` 列出各类规则的已公布年份和来源 ID，报告据此和方案假设年率核对每行标签，并与所得税的 `tax_law_year`、`rule_multiplier`、`policy` 交叉核对（Copilot 在 PR #11 指出：此前把推算年份整体改标为“当年已公布”可以通过报告检查）。测试保证它与引擎登记表一致。
- **新增已公布年份的流程**：读官方原文 → 引擎、验证器两份登记表和报告模板列表同时加入该年和来源 ID → 记录核对 → 从印刷表加已知答案。该年变为 `published`，以后各年改以它为基础推算，结果会变化，须单独开 PR 并重新生成报告。详见 [rules-provenance.md](rules-provenance.md)。
- **推算方法的局限**：官方指数化对不同税阶使用不同基年并做取整（见原文复核记录），模型用统一、不取整的假设年率，因此推算值与将来公布的数值会有差异；这正是要逐年标注的原因。
- **固定法定金额**（Pub 915 基数、NIIT 与附加 Medicare 门槛、税率、2025–2028 年的老年人增强扣除）不属于推算，按现行法律适用。

## 7. 已知限制与未完成门槛

- M0 范围签署（见决策记录草案）、M1 独立专业复核、实体移动设备验收、外部规划工具对照。
- IRS 截至 IR-2026-128（2026-10-23）尚未公布 2027 年税表、标准扣除和退休计划限额。
- `www.ssa.gov` 返回 403，SSA 网页示例本身未直接阅读（相关数值已通过 SSA 的 Federal Register 公告和 20 CFR 核对）。
- 1959 年出生者的 RMD 起始年龄 73 仍只有拟议规则依据，保留人工复核标记。

## 8. 建议的下一步

1. 负责人确认 [M0 决策记录](m0-scope-decision.md) 的五项决定（尤其 2b 州税和 2c 应税账户），据此选定 M2 第一组功能。
2. IRS 公布 2027 年收入程序后，按第 6 节流程单独提交“2027 年已公布数值”PR。
3. 若 2c 选择支持应税账户：实现股息和利息的逐年计税、资本损失抵扣与结转及其对 NIIT 的影响，贯穿输入、税务、提款、账本、报告和验证器，并补充独立案例。

## 9. 运维提示

- 本环境现在可以直接访问 `www.irs.gov` 和 `www.govinfo.gov`；`www.ssa.gov` 返回 403，`www.ecfr.gov` 和 federalregister.gov 的全文页面要求人机验证（Federal Register 的 JSON API 可用）。不要绕过这些验证。
- 安装 `fonts-noto-cjk` 前需先 `apt-get update`；浏览器验收可用预装 Chromium：`HFA_BROWSER_EXECUTABLE=/opt/pw-browsers/chromium`。
- 只使用虚构数据；报告 HTML 含明文财务数据，不要公开真实家庭文件。
