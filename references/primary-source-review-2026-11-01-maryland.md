# 原文复核记录：Maryland 州及地方所得税（M2 第二组，2026-11-01）

本记录说明 `maryland_tax.py` 与 `verify_outputs.py` 中 Maryland 规则的出处。所有文件在 2026-11-01 从官方网站直接下载或渲染阅读；PDF 记录 SHA256，网页（JavaScript 渲染的 Comptroller 知识库和 mgaleg 法条页面）记录所读文本的位置。`marylandcomptroller.gov`、`services.marylandcomptroller.gov`、`mgaleg.maryland.gov`、`dls.maryland.gov`、`www.irs.gov` 和 `www.ecfr.gov` 在本环境均可直接访问。

结论：未发现与登记值不一致的地方。2025 年会期的 BRFA（Chapter 604）改动对 2025 年及以后的税年生效；2026 年会期的 BRFA（HB 392）只改企业折旧脱钩等事项，未改个人税率、扣除、豁免、老年人抵免或资本利得附加税（见第 3 节）。专业复核尚未进行。

## 1. 文件与哈希

| 文件 | 网址 | SHA256 / 读取方式 | 用途 |
|---|---|---|---|
| 2025 Maryland State & Local Tax Forms & Instructions（居民说明书，60 页，PDF 修改日期 2026-04-21） | marylandcomptroller.gov/content/dam/mdcomp/tax/instructions/2025/resident-booklet.pdf | `17bc9f77e055c0570daee8840921e635b1b0952a39d54f28e33516699b9b6ba5` | 第 4 页豁免表 10A；第 6 页 Worksheet 13A；第 7 页第 10a、11 行；第 10 页 Worksheet 13D；第 13 页第 14 行和标准扣除；第 14 页 Instruction 17 税率表 I/II 及“$100,000 以下必须用税表”；第 16 页 code m 老年人抵免；第 17 页 Instruction 19 地方税和 2025 年地方税率表；第 26–32 页税表；第 34–44 页 Anne Arundel 税表和 Worksheet 19D；第 46 页 2026 年预估税工作表（相同税率表和 Anne Arundel/Frederick 2026 年税率） |
| 2025 Form 502 | …/tax/forms/2025/502.pdf | `4f4d604f27cf6995cbab58b7650fd812c0e4ccc9f8d899f04261ded5a04a24cf` | 第 1–34 行的计算顺序：第 20a、21b 行附加税；第 27 行“第 21–21b 行减去第 26 行，不低于 0” |
| 2025 Form 502CG 及说明 | …/tax/forms/2025/502cg.pdf | `8e0a3f2928d010aef85a28ac5480414875dc6778b4a2f57d3ae099bcddd6055f` | 第 1 行 = Form 502 第 1c 行（1040 第 7a 行），≤ 0 时为 0；第 2–7 行除外资产；第 9 行进入第 20a 行 |
| Tax Alert：2025 年会期标准扣除、逐项扣除和州/地方税率变化（2025-12-22 修订） | …/tax/legal-publications/alerts/tax-alert-changes-to-standard-and-itemized-deductions-and-to-state-and-local-income-tax-rates-from-the-2025-legislative-session.pdf | `55c38bf15260bd5c86fbe4e8ebabaf57c84d91e31c6c54bd980de73fe63bc5c0` | 新税阶 6.25%/6.50%；2% 附加税；标准扣除 $3,350/$6,700 并以后按 COLA 调整；地方税率上限 3.30%；2026 年 Allegany 3.03%→3.20%、Kent 3.20%→3.30% |
| Technical Bulletin 58：个人资本利得（2025-12-29 生效） | …/tax/legal-publications/technical-bulletins/tb-58.pdf | `7cd14115ebbc409060635cf6e26a2249d5f39be5f9913b197dbd89f34bd23c6e` | 附加税只对 FAGI 超过 $350,000 者征收，不论报税身份；对 Maryland AGI 中的净资本利得（IRC §1222(11)）征 2%；退休账户内资产等除外 |
| Technical Bulletin 51：老年人与 Maryland 所得税（2025-04-10，2024 税年数值） | …/tax/legal-publications/technical-bulletins/tb-51.pdf | `7030b69cd6130b34b58a41c7b16d8b0625564a6a6fda19cacf575a5716812c02` | 老年人抵免、两份收入减项、养老金排除资格（IRA 不合格）和社保免税的文字说明；其中 $39,500 是 2024 年上限，未使用 |
| Comptroller KB0010012“Maryland Pension Exclusion”（约 2026-04 更新） | services.marylandcomptroller.gov/taxes/en/maryland-pension-exclusion?…KB0010012 | 渲染文本，2026-11-01 | “For calendar year 2026, the maximum pension exclusion is $40,600”（2025 年 $41,200） |
| Comptroller KB“Maryland Income Tax Rates and Brackets” | services.marylandcomptroller.gov/taxes/en/maryland-income-tax-rates-and-brackets?… | 渲染文本，2026-11-01 | 2025、2026 年各县税率表及注 III（Anne Arundel 2026 分级）和注 IV（Frederick 2026 收入段） |
| 2026 年州及地方预扣信息（Central Payroll Bureau，2026-02-04） | …/md/state-payroll/memos/2026/2026-maryland-state-and-local-withholding-information.pdf | `4b8c4bc7dfece6737b4f9724274618dc7ec863b290f482b37c4a95035cc24534` | 2026 年州税阶与各县预扣税率（与 KB 一致的旁证） |
| DLS“Local Income Tax Rates in Maryland” CY2022–2026 | dls.maryland.gov/pubs/prod/NoPblTabPDF/2026CountyLocalTaxRates.pdf | `26f5a0a1d9cc7383242664ed5f1e7c82b3f816d1ea2a625f9875544011afa5a3` | 2026 年各县税率（旁证） |
| Tax-General Article §§10-105、10-106、10-207、10-209、10-211、10-217、10-754（mgaleg 现行文本） | mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gtg&section=… | 法条文本摘录的 SHA256 前 16 位：10-105 `a56ba48299f4900a`、10-106 `934ad54c455a4c83`、10-207 `50d49ec415c0a624`、10-209 `62d3fb296c465ee2`、10-211 `8181e2865fb39046`、10-217 `37996ce64046dfbf`、10-754 `d80b824657492d89` | 规则本身（第 2 节） |
| HB 392（2026 BRFA）财政与政策说明 | mgaleg.maryland.gov/2026RS/fnotes/bil_0002/hb0392.pdf | `0a42fc95fd8efdb6f165f5cfe1f3edc65eb37c1e3f37d9421d25917dc564cf5d` | 2026 年会期没有个人税率、扣除、豁免或抵免改动（第 3 节） |
| 2025 Instructions for Form 8960 | www.irs.gov/pub/irs-pdf/i8960.pdf | `b10fbb23ff4a053db197285497a00914c558e3ae0cdf5c956b7c0c7867376428` | 第 9b 行（州所得税）的说明（第 4 节） |
| 26 CFR 1.1411-4(f) | www.ecfr.gov（renderer API，current） | 渲染 HTML，2026-11-01 | (f)(3)：§63(d) 逐项扣除中可计入 NII 的项目，(iii) 为州所得税 |

## 2. 规则逐项核对

| 规则 | 原文 | 模型 |
|---|---|---|
| 州税率 | TG §10-105(a)(1)–(2)：单身 2%（$1–$1,000）…4.75%（至 $100,000）、5%（至 $125,000）、5.25%（至 $150,000）、5.5%（至 $250,000）、5.75%（至 $500,000）、6.25%（至 $1,000,000）、6.50%；合并申报 4.75% 至 $150,000、5% 至 $175,000、5.25% 至 $225,000、5.5% 至 $300,000、5.75% 至 $600,000、6.25% 至 $1,200,000、6.50% | 相同的边际税阶；说明书第 14 页的印刷基数（如单身 $100,000 → $4,697.50、合并 $1,200,000 → $69,822.50）作为已知答案 |
| 资本利得附加税 | §10-105(a)(3)–(4)：FAGI 超过 $350,000 时，对 Maryland AGI 中的净资本利得另征 2%；退休账户内资产、主要住宅等除外。Form 502CG 第 1 行取 Form 502 第 1c 行（1040 第 7a 行） | 基数 = max(0, 1040 第 7a 行)，FAGI 按美分判断 > $350,000；合格股息不计入（不属于第 7a 行）；模型中的资产都不属于除外资产（退休账户内交易不产生第 7a 行收益） |
| 地方税 | §10-106(a)：县税率 2.25%–3.30%，在县修改前持续有效；(c)：可分级。KB 2026 年表：除 Anne Arundel、Frederick 外为单一税率；Anne Arundel 分级（单身 2.70% 至 $50,000、2.94% 至 $400,000、3.20%；合并 $75,000/$480,000）；Frederick“对应收入段的纳税人适用该税率”（单身 2.25% ≤$25,000、2.75% ≤$50,000、2.96% ≤$150,000、3.20%；合并 $25,000/$100,000/$250,000） | 地方税 = 应税净收入（第 20 行）× 县税率；Anne Arundel 按边际累进（与说明书 Worksheet 19D 的基数 $1,350/$11,640/$2,025/$13,932 一致）；Frederick 按应税净收入所在收入段对全部收入适用一个税率。2027 年及以后沿用 2026 年税率（标为推算，乘数 1） |
| 社保 | §10-207(j)；说明书第 11 行：联邦 AGI 中的应税社保全部减除 | 减项 = 联邦 `taxable_social_security` |
| 养老金排除 | §10-209：年末 65 岁及以上（或残疾），雇主为雇员设立并按 401(a)、403、457(b) 合格的计划的养老金、年金收入；IRA、Roth IRA、展期 IRA、SEP、457(f) 除外；上限为 Comptroller 确定的金额减去本人领取的全部社保。Worksheet 13A 每位配偶单独一栏 | 合格收入 = 方案标为 `employee_retirement_system` 的养老金 + 本人 401(k) 的 RMD 和提款；传统 IRA 的提款和转换不合格；上限 2026 年 $40,600，以后按假设年率推算；残疾路径未建模 |
| 两份收入减项 | §10-207(r)：合并申报的双收入夫妻，减除 $1,200 与较低一方“修正后 Maryland AGI”（各自分别计算、不含本减项）的较小者；Worksheet 13D | 每人 = 本人工资（扣除税前缴款）+ 养老金 + 本人 IRA/401(k) 应税金额 + 共同持有收入的一半 − 本人养老金排除（应税社保在第 1 行计入、第 11 行减除，相互抵消）；共同持有收入（现金利息、应税账户利息和股息、1040 第 7a 行）按说明书 Instruction 8“jointly held … divided evenly”平分 |
| 标准扣除 | §10-217(b)：$3,350，合并申报 $6,700；(c)：2025 年之后每年按 IRC §1(f)(3) 的 COLA（以 2024 为基年）调整，增加额向下取整到 $50 的倍数，由 Comptroller 确定 | 2025 年为已公布值；Comptroller 尚未公布 2026 年金额（说明书第 46 页的 2026 年预估工作表仍印 $3,350/$6,700，这是预估用表，不视为 COLA 决定），因此 2026 年及以后按方案假设年率推算并标为推算，不做 $50 取整 |
| 豁免 | §10-211(b)–(c)：每人 $3,200；单身 FAGI 超过 $100,000 限为 $1,600，超过 $125,000 为 $800，超过 $150,000 为 $0；合并申报对应 $150,000/$175,000/$200,000；年末 65 岁及以上另加 $1,000（不递减） | 相同；FAGI 按美分判断；盲人豁免和受抚养人未建模 |
| 老年人抵免 | §10-754(b)：年末 65 岁及以上的居民，单身 FAGI 不超过 $100,000 抵免 $1,000；合并申报 FAGI 不超过 $150,000 抵免 $1,750，只有一方满 65 岁时 $1,000。(c)：若 9 月 BRE 预测比 3 月低 3.75% 以上，部分收入段的抵免减为 $500/$875。(d)：超过州税的部分不结转 | 相同；抵免以第 21–21b 行（含附加税）为限（Form 502 第 27 行）；假设 (c) 的收入预测触发条件不适用（无法预知），在报告和规则范围中写明 |
| 逐项扣除 | §10-217(a)(1)(ii)：联邦采用标准扣除时，州不能逐项扣除 | 联邦模型只用标准扣除，所以州也只用标准扣除 |
| 税表 | Instruction 17：应税净收入低于 $100,000 时必须使用税表（每行 $50） | 模型按税率表精确计算；第 26–32 页的税表行等于税率表在该行中点的税额四舍五入到美元（测试中核对 10 行州税表和 5 行 Anne Arundel 税表）。因此与实际申报相比，州税和地方税各可能相差约 $1–2；申报表的整美元取整也未模拟 |

## 3. 2026 年会期

HB 392（2026 BRFA）的财政说明列出的收入措施是：限制制造业 §168(k) 红利折旧、禁止 §168(n) 合格生产性财产折旧，以及若干基金与拨款调整，没有改动 §§10-105、10-106、10-207、10-209、10-211、10-217 或 10-754。HB 411（把标准扣除提高到 $4,100/$8,200）只举行了听证。mgaleg 的现行法条文本与上表一致。如之后发现 2026 年会期另有已生效的个人所得税改动，需按第 6 节的流程更新。

## 4. Form 8960 第 9b 行（交接说明第 8 节第 2 项）

26 CFR 1.1411-4(f)(3) 把 §63(d) 所述的逐项扣除列为可在计算 NII 时扣除的项目，其中 (iii) 是可分摊到 NII 的州所得税；2025 年 Form 8960 说明第 9b 行要求参照 Schedule A 说明中的限额。§63(e) 规定，未选择逐项扣除的个人不得享受任何逐项扣除。模型的联邦部分只采用标准扣除，因此**不**在第 9b 行扣除 Maryland 税，这样 NIIT 不会被低估。这一读法列为复核事项：如果复核人认为不逐项扣除时也可在第 9b 行扣除州税，需要同时修改引擎、验证器和 NIIT 案例。

## 5. 未建模事项（报告与规则范围中写明）

州附加项（如非 Maryland 市政债利息）、逐项扣除及其 7.5% 递减、受抚养人、残疾与盲人相关的豁免和养老金排除、军人和公共安全退休减项、联邦债券利息减项、退休林务员排除、百岁老人减项、劳动所得抵免、贫困线抵免、其他 502CR 抵免、地方抵免、在其他州缴税的抵免、部分年度居民和非居民、夫妻居住在不同县、税表与整美元取整。除 Maryland 以外的所有州一律拒绝，不按零税额处理。

## 6. 新增已公布年份的流程

当 Comptroller 公布新的标准扣除、养老金排除上限或县税率时：读取官方文件，在 `maryland_tax.PUBLISHED_*`、`verify_outputs.MD_*` 和报告模板的 `publishedStateRuleYears()` 中同时加入该年份和来源 ID，在本文件和规则来源登记表中记录，并补一个已知答案。该年份变为“已公布”，以后年份改以它为基数，结果会变化，应单独提交并重新生成报告。只改一处会使 `tests/test_rule_years.py` 或 `tests/test_maryland_tax.py` 失败。
