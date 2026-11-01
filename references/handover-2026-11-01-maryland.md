# 交接说明：M2 第二组“州税辖区接口与 Maryland”（2026-11-01）

供复核人、项目负责人或下一位接手的工程师（或代理）使用。接续[应税经纪账户的交接说明](handover-2026-10-29-taxable-account.md)（PR #12，已合并为 `d8f11b8`）。所有数据均为虚构示例。

## 1. 当前状态

| 项目 | 状态 |
|---|---|
| 分支 | `claude/serene-pascal-ehyo6g`，基于 `main` 的 `d8f11b8` |
| PR | 尚未创建（开 PR 后才会运行 GitHub Actions） |
| M2 第二组 | 工程交付完成：州税辖区接口；Maryland 全年居民的州及县/市所得税；输出契约 1.3 |
| 计算数值 | 仅联邦口径的方案逐字段不变；示例方案改为 Montgomery County 家庭，数值相应变化（第 5 节） |
| 本地验证 | 全部通过（第 4 节） |

## 2. 改动内容

| 文件 | 内容 |
|---|---|
| `scripts/state_tax.py`（新） | 辖区登记表与接口：校验、规则年份、计算、来源、范围说明；`excluded_with_disclosure` 保持仅联邦研究口径 |
| `scripts/maryland_tax.py`（新） | Form 502 受限子集；已公布年份登记（标准扣除 2025、养老金排除上限 2026、县税率 2026）；规则依据见[原文复核记录](primary-source-review-2026-11-01-maryland.md) |
| `scripts/audit_plan.py` | 校验调用辖区接口；每人的工资、养老金、社保和本人账户的应税金额传给州税；州税计入 `tax_due_total`；`state_tax` 行记录；Maryland 规则族进入 `rule_basis`；跨门槛的资金求解；引擎指纹增加两个文件 |
| `scripts/verify_outputs.py` | 重新录入全部 Maryland 常数，逐行独立复算；有方案时复算年龄、社保、合格养老金收入和两份收入份额；跨门槛留存现金的独立跳变检查 |
| `assets/audit-template.html` | Maryland 区块、税务拆解中的州税合计、规则依据文字、跨门槛提示、记录校验 |
| 测试 | `tests/test_maryland_tax.py`（印刷值已知答案、校验、集成、跨门槛、伪造）；`tests/golden/maryland-printed-cases.json`；3 个独立 Decimal 案例；报告与浏览器验收扩展；随机方案一半为 Maryland |

新输入（方案 schema 2.0 增量字段）：

```json
"tax_policy": {"jurisdiction": "US_federal", "reference_year": 2026, "filing_status": "mfj",
  "state_income_tax": {"jurisdiction": "US-MD", "residency": "full_year_resident",
    "local_jurisdiction": "montgomery_county", "pension_plan_types": {"person_a": "employee_retirement_system"}},
  "future_bracket_inflation": 0.025}
```

`local_jurisdiction` 取 23 个县（`<名称>_county`）或 `baltimore_city`；`pension_plan_types` 必须恰好列出有养老金金额的成员（没有则 `{}`），取值 `employee_retirement_system`（401(a)、403、457(b) 雇主计划）或 `not_employee_retirement_system`。原来的 `"excluded_with_disclosure"` 继续表示仅联邦研究口径。

## 3. 如何复现

```sh
sh scripts/verify_local.sh
python scripts/verify_m1_cases.py --output /tmp/m1-differences.json
python -m unittest discover -s tests -p test_maryland_tax.py -v
HFA_VERIFIER_FUZZ_PLANS=500 HFA_VERIFIER_FUZZ_SEED=7 python -m unittest discover -s tests -p test_verifier_independence.py -k test_valid_outputs
npm ci --ignore-scripts
sudo apt-get update && sudo apt-get install -y fonts-noto-cjk
HFA_BROWSER_EXECUTABLE=/opt/pw-browsers/chromium python scripts/collect_evidence.py --output /tmp/finance-evidence --browser
```

原文复核所用文件可按[原文复核记录](primary-source-review-2026-11-01-maryland.md)中的网址重新下载并用 SHA256 核对；Comptroller 知识库页面需要浏览器渲染。

## 4. 证据（本地结果）

见[验证记录](validation-report.md)的“M2 第二组”一节。要点：全部单元测试通过；40 年 / 300 路径的 Maryland 示例 9,444 条验证断言，追踪路径 17 共 9,524 条；9 个独立案例、18 个年度、1,140 项比较全部通过；随机方案（一半 Maryland、县随机）的有效结果、追踪路径和单字段篡改全部按预期通过或被拒绝；真实 Chromium 52 项检查通过。

数值不变的直接证据：用改动前（`d8f11b8`）和改动后的引擎分别运行仅联邦口径的示例、6 个原有 M1 案例和 145 个随机方案，152 个结果及其追踪路径逐字段相同（忽略新增的 `state_tax: null`、引擎指纹、契约版本和一行范围说明），另有 5 个方案两版都以相同信息拒绝。

## 5. 行为与兼容性变化

- **示例方案**：改为 Montgomery County（3.2%）的夫妻家庭，其他输入不变。2027 年：联邦 AGI $206,225，两份收入减项 $1,200，Maryland AGI $205,025，应税净收入 $197,985.81，州税 $9,529.26，县税 $6,335.55，合计 $15,864.80，总应付税款 $60,089.55。退休后 401(k) 提款享受养老金排除（例如 2057 年 $9,890.03）。
- **输出**：契约 1.3。每行新增 `state_tax`（仅联邦口径为 `null`）；`tax_due_total` 包含州及地方税；Maryland 方案的 `rule_basis` 多三类、`source_ids`/`rules_sources`/`rule_scope` 多 Maryland 条目；`tax.unmodeled` 在 Maryland 方案中去掉“state/local income taxes”。
- **引擎指纹**：现在覆盖 `audit_plan.py`、`tax2026.py`、`tax_extensions.py`、`state_tax.py`、`maryland_tax.py`；旧报告应重新生成。
- **验证器**：要求契约 1.3；含证据元数据的 1.2 结果会被拒绝。
- **资金求解**：出售亏损使联邦 AGI 跨过 Maryland 门槛（豁免递减、老年人抵免、$350,000 附加税、Frederick 收入段）时，州税的下降可能超过多出售的金额，不存在恰好付清税款的提款额。此时求解停在能付清全部支出和税款的最少提款处，多出的现金留在现金账户，记为 `state_tax.funding_cliff_excess_cash`，并在年度审计中提示。例：单身 70 岁、养老金 $101,000、支出 $83,000、成本远高于市值的应税账户（`tests/test_maryland_tax.py::FundingThreshold`）：出售 $1,000 使 FAGI 正好降到 $100,000，恢复 $3,200 豁免和 $1,000 抵免，$973.72 留在现金。没有这一处理时，引擎会报“未收敛”并拒绝整个方案。
- **报告**：年度审计新增 Maryland 区块；记录缺失、格式错误或与方案的辖区、县、成员不符时隐藏结论并禁用导出。
- **测试夹具**：断言联邦算术的测试夹具显式改为 `excluded_with_disclosure`。

## 6. 复核重点（请复核人确认）

1. **Form 8960 第 9b 行**：26 CFR 1.1411-4(f)(3)(iii) 把州所得税列为可计入 NII 的逐项扣除；联邦部分只用标准扣除（IRC §63(e)），所以模型不扣除。若认为不逐项扣除时也可扣除，需要同时改引擎、验证器和案例。
2. **共同持有收入平分**：两份收入减项需要每位配偶的修正后 Maryland AGI。模型把现金利息、应税账户利息和股息、1040 第 7a 行按一半归属每人（参照说明书 Instruction 8 对夫妻分别申报的规定）；方案没有记录账户的实际所有权比例。
3. **Frederick 县的收入段**：按 Comptroller 文字“for taxpayers who have a net taxable income between …”理解为整段收入适用一个税率（在段界有跳变），而 Anne Arundel 是边际累进。请确认。
4. **老年人抵免的收入预测触发条件**：TG §10-754(c) 在 9 月收入预测比 3 月低 3.75% 以上时把部分收入段的抵免减为 $500/$875。未来年份无法预知，模型假设不触发。
5. **401(k) 视为“employee retirement system”**：雇主设立、按 401(a) 合格；模型中没有自雇，所以全部 401(k) 提款都算合格收入。养老金则由用户逐一声明。
6. **标准扣除的推算**：2026 年起按 COLA 调整且增加额向下取整到 $50；Comptroller 尚未公布 2026 年金额，模型按假设年率推算，不做 $50 取整，并标为推算。

## 7. 已知限制与未完成门槛

- 未建模：州附加项、逐项扣除、受抚养人、残疾与盲人、军人和公共安全退休减项、联邦债券利息减项、其他抵免、地方抵免、部分年度居民、夫妻居住在不同县、税表与整美元取整（与实际申报可能差 $1–2）。
- 复核人姓名、资质与问题清单仍未记录（M0 正式退出条件）；M1 独立专业复核、实体移动设备验收、外部规划工具对照、市场数据来源仍待完成。
- IRS 2027 年税表、标准扣除和退休计划限额仍未公布；Maryland 2026 年标准扣除也未公布。

## 8. 建议的下一步

1. 负责人补写复核人信息；请复核人审阅第 6 节以及应税账户交接说明第 6 节的事项。
2. 开 PR 运行 CI（含真实 Chromium 验收），根据评审意见修正。
3. IRS 2027 年收入程序或 Maryland 2026 年标准扣除公布后，各自单独提交“已公布数值”更新（流程见原文复核记录第 6 节）。
4. M3：按决定 3 从收入记录重建社保。

## 9. 运维提示

- 本环境可直接访问 `marylandcomptroller.gov`、`mgaleg.maryland.gov`、`dls.maryland.gov`、`www.irs.gov` 和 `www.ecfr.gov`；`services.marylandcomptroller.gov` 的知识库页面由 JavaScript 渲染，用已安装的 Playwright/Chromium 读取。
- 浏览器验收：`npm ci --ignore-scripts`、安装 `fonts-noto-cjk`、`HFA_BROWSER_EXECUTABLE=/opt/pw-browsers/chromium`。
- 只使用虚构数据；Maryland 方案只需要县或 Baltimore City，不要加入街道地址。
