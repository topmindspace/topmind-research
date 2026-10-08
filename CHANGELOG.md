# Changelog

## Unreleased

### 优化

- GitHub Actions 改用 Node 24 运行时的版本：`actions/checkout` v4 → v7、`actions/setup-python` v5 → v7、`actions/upload-artifact` v4 → v7（ci 与 sources-weekly）。
- `runs-on` 由 `ubuntu-latest` 固定为 `ubuntu-24.04`：GitHub 在 2026-10-19 至 11-19 期间把 `ubuntu-latest` 逐步切到 Ubuntu 26.04，先停在当前已验证的镜像，切 26.04 另行验证后再改。

## 0.2.2 — 2026-10-08

### 优化

**出稿交接**

- 公众号排版与定稿统一交给 `topmind-wechat-post`（topmind-writing-skills），与 topmind-skills 路由表同步；`SKILL.md`、`references/upgrade-rules.md`、周报模板、README、评测用例一并更新
- `scripts/check_skill_refs.py` 增加检查：技能文件里再出现旧名 `topmind-wechat` 即报错
- 写明出稿技能只产出稿件、发布由用户操作，本技能和下游技能都不代发

**与 topmind-presentation 分工**

- description 的 Do NOT 增加「把已有材料做成多页 HTML / PPTX 汇报 → topmind-presentation」
- 「做一份 X 的研究报告」先在本技能收证据，做汇报材料只在回执建议 presentation，不自动链式调用；评测集补 a12、a13 两条

**信源巡检**

- `sources-weekly.yml` 去掉 `|| true`：字段检查不通过、或 `status: ok` 的信源失效（404/410、域名解析失败、连接被拒）时运行标红
- 403、429、5xx、超时、证书链问题记为警告注释，不标红；完整报告写进运行摘要，并作为 artifact 保留 30 天
- `scripts/check_sources.py` 增加 `--strict`、`--report`；超时单独记为 `Timeout`，不再和连接失败混在一起
- 不自动改配置、不自动开 issue

**安装**

- README 写明本技能未发布到 npm，给出 skills CLI（`npx skills add topmindspace/topmind-research`）和 git clone 两种装法，并提示不要用 topmind-skills 的 pack 安装器
- 根 `package.json` 增加 `files` 白名单（技能目录、README、LICENSE、CHANGELOG，排除 Python 缓存），为以后上 npm 做准备；本版不发布 npm

**analyze**

- 对比档位起子 agent 前先在回复里列计划表，用户可中途改
- 每轮反思补洞的缺口清单写进状态文件「待办」，中断后可接着补

## 0.2.1 — 2026-10-08

> **不兼容变更**：三个技能合并为单技能 `topmind-research`，collect / analyze 改为技能内的两种模式，`topmind-research-collect`、`topmind-research-analyze` 不再单独发布。
>
> **升级方法**：删除宿主技能目录里旧的 `topmind-research`、`topmind-research-collect`、`topmind-research-analyze` 三个目录，再把本仓库的 `topmind-research/` 整个复制进去。改过 `config/sources.yaml` 的，先备份，复制后按新字段（见文件头说明）合并回去。非 topmind 工作区运行过 collect 的，watermark 位置改为 `~/.topmind-research/collect-watermark.md`，首次运行会读旧位置 `research/collect-watermark.md` 沿用。

### 优化

**结构**

- 技能目录自包含：`config/`、`references/` 移入 `topmind-research/`，路径一律相对技能根目录
- 根 `package.json`、技能 `package.json`、`SKILL.md`、`scripts/collect_feeds.py` 的版本统一为 0.2.1，补充 repository 字段
- 去掉对外部技能 topmind-tool-scout 和宿主未必提供的 wide_research 工具的引用，工具储备条目格式写入 `references/collect.md`

**核验门**

- `references/verification.md` 按事实类型定核验强度：公司发布 1 个 T0 并标厂商口径，第三方数字 2 个独立来源，论文以原文为准，传闻不进结论
- 逐句 `[n]` 引用与统一来源表格式，交付前做引用支撑检查并写核验记录；译名教训移到 `references/errata.md`
- 分级表增加「独立评测方」（Artificial Analysis、LMArena，只限其自己的评测结果算 T1），与脚本里 benchmarks 记 T1 一致
- 官方 RSS 摘要可支撑「发布了什么、哪天发布」，数字、价格、基准、规格要读到正文；Hugging Face 博客按实际发文组织记发布方；付费墙来源注明只读到摘要

**collect 排序**

- 排序改为先分桶再打分：论文源只作候选池，要有筛选信号（HF 每日论文点赞 ≥ 10、官方博客或技术报告提及、命中用户方向）才进「论文速递」，最多 5 篇，不再参与主榜
- 来源分改为按事实类型是否达到核验最低要求打分，融资并购等第三方数字条目达标即满分
- 主榜同一公司最多 3 条；「融资并购」「政策监管」各保 1 个名额（要有达标条目）
- 「距今」按 UTC+8 日历日计，只有日期的条目按当日 00:00（UTC+8）
- HF / GitHub 抓到的新模型、新仓库作为「发布信号」单列，核实为正式发布后再进主榜

**collect 流程**

- 信源状态区分「抓到 0 条」「没抓到」「覆盖不全」三种情况，脚本的覆盖警告照抄进周报
- last30days 写明检测方法（`~/.agents/skills/last30days/SKILL.md` 与 `SETUP_COMPLETE=true`），未安装、未完成首次配置时改用 HN / Reddit 公开讨论帖作 T3 社区线索（每个发布最多 2 帖，不做概括判断），回执给出安装或配置提示
- collect 增加工具调用参考预算（40–60 次，超过 80 次收尾）和单信源停止规则
- 非 topmind 工作区的 watermark 改到固定位置 `~/.topmind-research/collect-watermark.md`
- 分类增加「公司动态」；周报模板增加「排序记录」「回执」可选节，「信源状态」按三种情况分写

**analyze 与交接**

- analyze 增加研究简报与计划确认、投入档位（单点 / 对比 / 综述）及档位判定标准（2–4 个具体对象为对比，一类或超过 4 个为综述）、子 agent 并行上限 6 且不递归、最多 2 轮补洞、研究完成后单次写作
- 出稿交接在 `SKILL.md`、`references/upgrade-rules.md`、`evals/queries.yaml` 三处统一：短稿或快讯 → topmind-briefs，公众号排版与定稿 → topmind-wechat，其他长文 → topmind-write，未安装 → topmind-write，只在回执建议，与 topmind-skills `shared/trigger-disambiguation.md` 一致
- 用户授权深挖但未点名时，列候选请用户选择，不由 agent 代选（与 topmind-skills 路由表「未经用户点名不自动深挖」一致）
- 不再自动写记忆、自动改 `sources.yaml`、自动升级深挖、自动调用出稿技能，统一改为回执建议 + 用户确认
- 新增断点续跑状态文件（`references/state.md`）与五个输出模板（`assets/templates/`），沉淀 frontmatter 与 topmind-organize 约定对齐

**信源（`config/sources.yaml`，2026-10-08 逐条核验）**

- 字段：新增 `rss_extra`、`hf_api`、`gh_api`、`papers_api`、`list_api`（及 `list_api_method` / `list_api_body`）、`sitemap`、`podcast`、`headers`、`ca_root`、`x_account`；`fetch` 增加 `js`（前端渲染）、`api`、`x`；`status` 改为 ok / page-only（可打开但不可机读）/ blocked / tbd，只有能拿到带日期条目的信源标 ok
- Meta：ai.meta.com/blog/ 转 ok，无 RSS，列表需按日期重排，请求头按 `headers: browser`（只带 Chrome UA 不带 Sec-Fetch-* 时返回 400）
- Perplexity：/hub/blog 被 Cloudflare 人机验证拦截，标 blocked、`fetch: x`，博文发布用官方 X @perplexity_ai 确认；补官方 API 更新日志 RSS（只覆盖 API）
- 百度：改为官方 ERNIE Blog（ernie.baidu.com/blog）及其 RSS `/blog/index.xml`，RSS 相对链接由脚本补全域名
- 华为：改为华为云新闻中心 huaweicloud.com/news.html（全量新闻，无 AI 筛选；huawei.com/cn/news 为前端渲染，不用）
- 商汤：改为中文新闻中心 sensetime.com/cn/news
- 晚点 LatePost：改为 www 子域列表页，经 `list_api`（POST get-news-data）读取；证书链到 Let's Encrypt 新根 ISRG Root YR，记 `ca_root`，缺根证书时用 `--ca-bundle` 追加
- 中国厂商：千问、混元、MiniMax、阶跃、百川标 `fetch: js`；DeepSeek、月之暗面、智谱、千问、字节 Seed、腾讯、小米 MiMo、MiniMax、阶跃、零一万物、百川补 Hugging Face 组织 API 与 GitHub 组织仓库 API（均于 2026-10-08 请求验证，note 写明最新一条日期）；DeepSeek 新闻改为 /news/ 并补 sitemap
- 公司官方 X 账号：@deepseek_ai、@Kimi_Moonshot、@Zai_org、@MiniMax_AI、@StepFun_ai、@Alibaba_Qwen、@BaichuanAI、@ByteDanceSeed_、@ErnieforDevs、@SenseTime_AI、@perplexity_ai、@AIatMeta
- 人物：梁文锋 `x_handle: null`（本人无 X 账号，@LiangWenfeng_ 为仿冒号，附 Reuters、SCMP 依据）；姜大昕保持 TBD，记候选 @DaxinJiang（未确认）；杨植麟、张鹏、闫俊杰、王小川、周靖人、朱文佳保持 TBD，note 写明用哪个公司官方号代替，王小川记微博；新增 `x_status` 字段
- 论文源：移出 Semantic Scholar（只有主页，无可扫列表）；HF Papers 补每日论文 API 作筛选信号；Hacker News 交给 last30days，Papers with Code 跳转到 HF Papers，移出
- 千问当前官方博客入口未能确认（qwen.ai 为前端渲染，其列表接口最新到 2025-12-23，qwenlm.github.io/blog 停在 2025-09-23），暂不替换，发布信号以 HF / GitHub / X 为准
- 此前已完成：新智元地址更正为 aiera.com.cn；字节改为 Seed 官网；小米改为 MiMo 官网；LMArena 补地址；人物 X 账号补全 7 个（经 X 接口核对）

**脚本**

- `collect_feeds.py`：日期按 published > pubDate > issued > date > updated 的优先级取，不再按 XML 出现顺序；统一转成 UTC+8 后按时刻排序；标题做 HTML 实体解码；截断时保留最新的条目，默认每个渠道 100 条
- `check_citations.py`：来源节标题认「参考资料」「参考文献」等同义词；来源行缺级别或「发布」字段、付费墙域名给警告
- `check_sources.py`：按新的 status / fetch 取值和人物字段校验，可达性巡检按信源 `headers` 档位请求
- 脚本不再在技能目录生成 `__pycache__/`

### 特性支持

- `collect_feeds.py` 支持 `rss_extra`、`hf_api`、`gh_api`（仓库与 releases）、`papers_api`（按窗口逐日取 HF 每日论文）；输出增加 section / kind / channel / publisher / arxiv_id 字段
- `collect_feeds.py` 覆盖检查：最早一条晚于窗口起点、条目被截断时写警告；`--report` 输出「信源状态」Markdown，分出「窗口内 0 条」「未抓到」「覆盖警告」「须按页面读取」
- `collect_feeds.py` 与 `check_sources.py` 支持 `--ca-bundle`（或环境变量 `TOPMIND_CA_BUNDLE`、本机副本里的信源 `ca_bundle` 字段）追加 CA 文件，应对缺新根证书的环境；证书校验始终开启，不提供关闭开关
- 请求头可按信源配置（`headers`: default / browser / none）
- 新增 `scripts/rank_items.py`：按 collect 第 5 步分桶、打分、公司上限、分类保底，合并 agent 补充字段，`--format md` 输出「排序记录」
- `check_citations.py --count`：统计带引用的句子数，供「核验记录」使用
- `check_versions.py` 同时检查 `collect_feeds.py` 的 VERSION
- 评测：`evals/rubric.md` 为 collect 增加「排序质量」「信源覆盖」两个维度，collect 满分 18、合格 ≥ 14；`evals/queries.yaml` 增至 23 条（授权未点名深挖、融资监管方向排序、briefs 交接）
- 仓库检查与 CI：版本一致、技能内引用完整、信源字段、隐私扫描、单元测试、`agentskills validate`；每周信源可达性巡检
- 可选 Gemini Deep Research 后端说明（`references/backend-gemini.md`），仅在用户明确要求时使用
- 英文 README

## 0.2.0 — 2026-10-07

- 信息源扩充：核实 xAI（x.ai/news）、MiniMax（minimax.io）；新增 benchmarks（Artificial Analysis、LMArena）、newsletters（TLDR AI、The Batch）、论文源（Papers with Code、Semantic Scholar）、工具源（Product Hunt、Hacker News）、媒体（晚点 LatePost）；关键人物增至 16 位
- 工作流优化：新增 `references/input-guide.md`（输入方式矩阵、增量 sweep watermark 机制、analyze 置信度标注）
- 核实机制新增第五节隐私保护：只收录公开信息源，输出脱敏，配置中禁放密钥
- 状态为 tbd 的来源待后续核实后转正

## 0.1.0 — 2026-10-07

- 首版：`topmind-research` 路由 + `topmind-research-collect` + `topmind-research-analyze`
- 配置化：`config/sources.yaml`（20 余家公司/关键人物/媒体/论文源/工具源）、`config/categories.yaml`
- 核实机制 `references/verification.md`、升级/回流规则 `references/upgrade-rules.md`
- 吸收替代 `topmind-tool-scout`（储备库格式与 2026-W41 成果迁移）
