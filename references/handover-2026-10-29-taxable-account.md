# 交接说明：M0 首发范围确认与 M2 第一组“应税经纪账户”（2026-10-29）

供复核人、项目负责人或下一位接手的工程师（或代理）使用。接续[按年份管理规则的交接说明](handover-2026-10-29-rule-years.md)（PR #11，已合并为 `6b8f74c`）。所有数据均为虚构示例。

## 1. 当前状态

| 项目 | 状态 |
|---|---|
| 分支 | `claude/epic-maxwell-5xrz9u`，基于 `main` 的 `6b8f74c` |
| PR | 尚未创建（`claude/*` 分支推送不触发 GitHub Actions，开 PR 后才会运行） |
| M0 | 项目负责人已确认五项决定（[决策记录](m0-scope-decision.md)）；复核人已指定，姓名、资质和问题清单待记录 |
| M2 第一组 | 工程交付完成：应税账户的股息、利息、资本利得分配、出售亏损、$3,000 抵扣上限与结转、NIIT；输出契约 1.2 |
| 计算数值 | 旧口径方案逐字段不变；示例方案改用新口径，数值相应变化（第 5 节） |
| 本地验证 | 全部通过（第 4 节） |

## 2. 改动内容

| 提交 | 内容 |
|---|---|
| M0 决策记录 | 五项决定写入决策记录、支持范围和 ROADMAP；Skill、README 和隐私说明改为宿主中立（Codex / Claude Code），写明模型提供方数据流和安装位置 |
| M2 第一组 | `tax2026.federal_tax` 增加 Schedule D 净额、$3,000 上限、按 §1212(b) 的结转、合格股息并入优惠税率；`audit_plan` 增加新口径的输入校验、分配计算与再投资、亏损确认、跨年结转；NIIT 基数扩大；`verify_outputs` 逐项独立复算；报告新增“应税账户：分配、出售与资本损失”区块；两个独立 Decimal 案例；原文复核记录 |

新输入（方案 schema 2.0 增量字段）：

```json
"accounts": [{"id": "brokerage", "kind": "taxable", "balance": 300000, "basis": 250000,
  "gain_treatment": "long_term_proportional_with_distributions",
  "annual_distributions": {"qualified_dividend_yield": 0.012, "nonqualified_dividend_yield": 0.002,
    "taxable_interest_yield": 0.008, "capital_gain_distribution_yield": 0.002, "handling": "reinvested"}}],
"capital_loss_carryover_into_2027": 0
```

四个收益率都必须写明（可为零）；只支持再投资；结转额是上一年 Schedule D 的结转合计（短期、长期之和；模型中没有短期收益，两者区分不影响结果，推导见 `tests/test_taxable_account.py`）。旧口径 `long_term_proportional_no_loss_offset` 保留用于重放旧方案，不能带分配或正的结转额，不应用于专业人员辅助场景。

## 3. 如何复现

```sh
sh scripts/verify_local.sh
python scripts/verify_m1_cases.py --output /tmp/m1-differences.json
python -m unittest tests.test_taxable_account -v
HFA_VERIFIER_FUZZ_PLANS=500 HFA_VERIFIER_FUZZ_SEED=7 python -m unittest discover -s tests -p test_verifier_independence.py -k test_valid_outputs
npm ci --ignore-scripts
sudo apt-get update && sudo apt-get install -y fonts-noto-cjk
HFA_BROWSER_EXECUTABLE=/opt/pw-browsers/chromium python scripts/collect_evidence.py --output /tmp/finance-evidence --browser
```

原文复核所用文件可按[原文复核记录](primary-source-review-2026-10-29-taxable-account.md)中的网址重新下载并用 SHA256 核对。

## 4. 证据（本地结果）

见[验证记录](validation-report.md)的“M2 第一组”一节。要点：233 个测试通过；40 年 / 300 路径示例 6,868 条验证断言；6 个独立案例、14 个年度、818 项比较全部通过；随机抽样的有效结果、追踪路径和单字段篡改全部按预期通过或被拒绝；真实 Chromium 44 项检查通过。

数值不变的直接证据：用改动前（`6b8f74c`）和改动后的引擎分别运行旧示例、4 个原有 M1 案例、3 个高工资变体（其中一个两版都以相同信息拒绝）和一个负收益、高成本基础的亏损变体，全部 300 条路径的结果及追踪路径逐字段相同（忽略新增字段、来源链接和说明文字）。

## 5. 行为与兼容性变化

- **示例方案**：经纪账户改用新口径（虚构收益率 1.2% / 0.2% / 0.8% / 0.2%，结转 0）。首年联邦所得税 25,684 → 26,974 美元（+1,290 = 3,000 普通收入 × 22% + 4,200 优惠所得 × 15%）；确定性路径 40 年税款合计 +65,642；期末实际资产中位数 1,838,733 → 1,796,069；资金满足比例不变（92.7%）。
- **输出**：契约 1.2。每行新增 `taxable_accounts`；`tax` 新增 13 个字段，其中 `capital_loss_adjusted_taxable_income` 只在净亏损年份有值，否则为 `null`；`realized_ltcg` 在新口径下可为负；`tax.unmodeled`、`rules_sources`、`source_ids` 和 `rule_scope` 文字更新。AGI 可为负。
- **引擎指纹**：`audit_plan.py`、`tax2026.py`、`tax_extensions.py` 均有改动；旧报告应重新生成。
- **验证器**：要求契约 1.2；含 `evidence_status` 的 1.1 结果会被拒绝。没有证据元数据的更早结果仍按旧口径验证。
- **报告**：年度审计新增应税账户区块；旧口径出售亏损和“结转加回 §151 扣除”两类提示；新字段缺失、口径未知或格式错误时隐藏结论并禁用导出。
- **API**：`tax_extensions.net_investment_income_tax` 接受负的 MAGI；`tax2026.taxable_social_security` 接受负的其他收入；`federal_tax` 新增关键字参数，默认值保持旧行为。

## 6. 复核重点（请复核人确认）

1. **结转计算加回 §151 扣除**：IRC §1212(b)(2)(B) 的“调整后应税所得”加回 §151 允许的扣除，而 Pub. L. 119-21 把 2025–2028 年的 $6,000 老年人扣除写在 §151(d)(5)(C)。引擎按法条加回。IRS 现有工作表（2025 年说明，结转自 2024 年）早于该扣除，只用应税所得；适用于 2025 年起结转的 2026 年说明尚未发布。差异只在“亏损年份、应税所得（未截零前）为负、且有老年人扣除”时出现，报告会逐年提示。
2. **全部视为长期**：再投资份额持有不满一年，年末按比例出售时可能含短期部分（Pub 550 p. 83）；模型统一视为长期。
3. **收益率是假设**：分配收益率由用户给定，模型不核实合格股息的持有期要求，不支持 1099-DIV 2b/2c/2d、资本返还、免税利息股息、§199A 和外国税收抵免。
4. **未建模**：洗售、批次选择、Form 8960 第二部分扣除（投资费用、州所得税——接入 Maryland 后需复核）。

## 7. 已知限制与未完成门槛

- 复核人姓名、资质与问题清单；M1 独立专业复核；实体移动设备验收；外部规划工具对照；市场数据来源。
- IRS 2027 年税表、标准扣除和退休计划限额截至 IR-2026-129（2026-10-29）仍未公布。
- `www.ssa.gov` 在本环境返回 403（M3 从收入记录重建社保时需要放行或改用 Federal Register / eCFR）。

## 8. 建议的下一步

1. 负责人补写复核人姓名与资质；请复核人审阅第 6 节和 [M0 决策记录](m0-scope-decision.md)，列出问题清单。
2. M2 第二组：州税辖区接口与 Maryland（全年居民；县/Baltimore City 地方税必填；州的加减项、社保减免、养老金排除、资本利得附加税等按税年登记并读 Comptroller of Maryland 原文）。接入后复核 Form 8960 第 9b 行（州所得税）是否适用。
3. IRS 公布 2027 年收入程序后，单独提交“2027 年已公布数值”PR。
4. M3：按决定 3 从收入记录重建社保。

## 9. 运维提示

- 本环境可直接访问 `www.irs.gov` 和 `www.govinfo.gov`；`uscode.house.gov` 当前为临时页面，法条改用 govinfo 的 US Code 版本。
- 浏览器验收：`npm ci --ignore-scripts`、安装 `fonts-noto-cjk`、`HFA_BROWSER_EXECUTABLE=/opt/pw-browsers/chromium`。
- 只使用虚构数据；报告 HTML 含明文财务数据；agent 读入的数据会发送给模型提供方。
