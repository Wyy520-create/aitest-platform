# aitest-platform 智能接口测试平台

> 测试开发作品集：一个"自产自销"的全链路闭环——**自己写被测系统（埋 5 个真实缺陷）→ 自己写分层测试引擎（45 用例、缺陷全命中）→ 自己搭测试平台（用例管理 / 双执行器 / AI 生成 / RAG 问答）→ CI 用"预期签名"守门**。

![CI](https://github.com/Wyy520-create/aitest-platform/actions/workflows/ci.yml/badge.svg)

## 这是什么

传统练习项目的尴尬：被测系统是别人的，用例是"练习题"，缺陷发现能力无法自证。本项目的解法是把整条链路全部自己做：

- **被测系统 mini-mall**：迷你电商（用户/JWT 鉴权、商品、购物车、订单），**有意注入 5 个真实感缺陷**——水平越权、并发超卖、金额精度、参数校验缺失、分页静默错误（清单见 `docs/BUGS.md`）；
- **测试引擎**：Pytest 分层架构 45 用例，其中 7 条缺陷检测用例（`test_bug` 前缀）**全部命中**注入缺陷——引擎的发现能力是可证明的，而不是"跑全绿"的自嗨；
- **测试平台**：用例管理、双执行器（套件执行 / 配置化执行）、执行记录、ECharts 看板；
- **AI 工场**：LLM 生成用例草稿 → 人工评审门禁（采纳 / 驳回附因）→ 入库即可执行；无 API key 自动降级 Mock，全链路照常可跑；
- **RAG 问答**：自实现 BM25 检索项目知识库，知识库外问题**拒答**（幻觉防护），检索层质量用 21 条 7 类场景评测集量化并进 CI；
- **CI**：缺陷注入仓库的关键姿势——**不断言"全绿"，断言"预期签名"**（45 用例 / 38 通过 / 7 失败 / 7 条失败全为缺陷检测用例）。

## 项目组成

| 模块 | 说明 | 技术 |
|------|------|------|
| `sut/` | 被测系统 mini-mall：5 注入缺陷 + TEST_MODE 数据工厂路由 | FastAPI + SQLAlchemy + SQLite |
| `engine/` | 分层接口自动化引擎：core 客户端 / cases 用例 / conftest 依赖注入 | Pytest + Requests + junitxml |
| `platform/backend/` | 平台 API：用例 / 执行 / AI 生成 / RAG 问答 / 看板 | FastAPI + SQLite |
| `platform/frontend/` | 单文件 SPA：登录 / 看板 / 执行中心 / 用例管理 / AI 工场 / RAG 问答 | Vue3 + Element Plus + ECharts（CDN vendor 本地化，离线可交付） |
| `platform/backend/app/rag/` | BM25 自实现 + 得分率拒答 + 7 类场景质量评测 | 纯 Python 标准库，零第三方依赖 |
| 编排 | 4 服务容器编排 + CI 三 job | docker compose + GitHub Actions |

## 架构

```text
浏览器 ──► nginx :3000
            ├── 静态前端（Vue3 单文件，依赖 vendor 本地化）
            └── /api/* 同源反代（无 CORS 问题）
                    │
                    ▼
            平台后端 FastAPI :8100 ──► SQLite（用例/执行记录，VOLUME 持久化）
                    │
        ┌───────────┼──────────────────────┐
        ▼           ▼                      ▼
   执行调度         AI 工场                RAG 问答
   subprocess     LLM 生成草稿            自实现 BM25 检索 docs/ 语料
   engine/run.sh  → 评审门禁 → 入库        相关度得分率 < 0.055 → 拒答
        │        （无 key 降级 Mock）      ≥ 0.055 → 拼 Prompt → LLM
        ▼                                  （无 key 降级"检索直出"）
   Pytest 45 用例 ──► 被测系统 mini-mall :8000
                     （5 注入缺陷；TEST_MODE=1 才注册数据工厂路由）

CI（每次 push 三个 job）：
   api-tests      引擎容器跑全套 → verify_suite.py 校验预期签名 45/38/7/7
   platform-e2e   全栈 compose 起 → 登录 → 触发执行 → 断言签名 → 前端探活
   rag-eval       21 条 7 类检索质量评测（标准库直跑，零依赖）
```

## 质量指标（当前实测）

| 维度 | 指标 | 结果 |
|------|------|------|
| 引擎 | 用例总数 / 通过 / 失败 | 45 / 38 / 7 |
| 引擎 | 缺陷检测用例命中注入缺陷 | 7/7 全命中，5 个缺陷全覆盖 |
| 引擎 | 可重复执行（随机测试数据，不依赖初始库） | 连续多轮执行签名一致 |
| RAG 检索层 | hit@3 / MRR / 拒答正确率（21 条 7 类评测集） | 1.0 / 0.972 / 1.0 |
| RAG 一致性 | 本地 / 容器 / CI 三端同语料同指标 | 完全一致 |
| AI 工场 | 无 key 降级 | Mock 生成可用草稿，评审流照常 |

## 快速开始

### 方式一：容器一键起（推荐）

```bash
git clone https://github.com/Wyy520-create/aitest-platform.git
cd aitest-platform
docker compose up -d          # sut + backend + frontend 三服务
```

浏览器访问 `http://localhost:3000`，登录 `admin / admin123`：
执行中心跑一次"套件执行" → 看板应显示 45 用例 / 38 通过 / 7 失败 / 命中缺陷 7。

### 方式二：本地开发

```bash
# 终端 1：被测系统
cd sut && uvicorn mini_mall.main:app --port 8000
# 终端 2：平台后端
cd platform/backend && uvicorn app.main:app --port 8100
# 终端 3：前端静态服务
cd platform/frontend && python3 -m http.server 5500
```

访问 `http://localhost:5500`（前端按端口自动切换 API 地址）。

### 跑 RAG 质量评测（CI 同源命令）

```bash
python3 scripts/eval_rag.py   # 退出码 0=全部通过，1=有未通过
```

## 核心设计决策

- **缺陷注入 + 预期签名**：CI 不断言全绿，而是断言 `45/38/7/7`（`scripts/verify_suite.py`）——注入缺陷被误修、或套件被改坏，CI 都会挂红；
- **命名约定替代 marker 传递**：pytest marker 不进 junitxml，缺陷检测用例用 `test_bug` 前缀，平台与 CI 按前缀统计命中数；
- **双执行器**：套件执行（整套 45 条）+ 配置化执行（单条用例参数由平台下发），覆盖"回归"与"定向验证"两种真实工作流；
- **测试数据工厂**：`TEST_MODE=1` 才注册 `/api/dev/*` 路由——生产环境该攻击面**根本不存在**（不是鉴权挡住，而是没有这个面）；引擎 fixture 两级降级（本地直连 SQLite → 容器走 HTTP 工厂）；
- **AI 评审门禁**：LLM 只产草稿，人评审（采纳率/驳回理由）才入库——AI 是提效不是放权；
- **RAG 拒答用"得分率"而非绝对分**：BM25 绝对分与查询长度正相关，口语化短查询会被误拒（实测踩坑）；除以该查询理论满分（`ideal_score`）后跨长度可比，阈值才有意义；
- **RAG 语料治理**：只有稳定自包含的 `docs/` 知识文档进语料，README 这类频繁变动的导航文档刻意排除——本地/容器/CI 三端评测输入完全一致。

## 目录结构

```text
aitest-platform/
├── sut/mini_mall/          # 被测系统（5 注入缺陷 + dev_tools 数据工厂）
├── engine/
│   ├── core/               # API 客户端（鉴权/断言/随机数据）
│   ├── cases/              # 45 用例（auth/product/cart/order/bug_*）
│   └── conftest.py         # 依赖注入组装 + 数据工厂两级降级
├── platform/
│   ├── backend/app/
│   │   ├── routers/        # auth/case/execution/ai/qa
│   │   ├── ai/             # LLM 接入（DeepSeek/Mock 降级）+ 评审
│   │   ├── rag/            # bm25 / knowledge / qa / evaluator + 评测集
│   │   └── runner.py       # subprocess 执行 + junitxml 解析
│   └── frontend/           # index.html 单文件 SPA + vendor/ 本地依赖
├── docs/                   # BUGS.md / RAG_KNOWLEDGE.md / LLM_SETUP.md
├── scripts/                # verify_suite.py / eval_rag.py
├── docker-compose.yml      # sut + backend + frontend（engine 为 tools profile）
└── .github/workflows/ci.yml # api-tests / platform-e2e / rag-eval
```

## 推荐学习路径

> 本项目代码注释即教学线索，建议按依赖顺序读：

1. **`docs/BUGS.md`** — 5 个缺陷的现象/根因/正确写法，一切故事的起点；
2. **`engine/`** — conftest 依赖注入组装 → core 客户端 → cases 45 用例（注意 7 条 `test_bug` 前缀的断言写法）；跑 `bash engine/run.sh` 对照 junitxml；
3. **`scripts/verify_suite.py`** — "预期签名"如何校验，CI 的第一课；
4. **`platform/backend/app/`** — routers（API 契约）→ runner.py（执行调度与命中统计）→ ai/（生成/评审/Mock 降级）→ rag/（BM25 打分、得分率拒答、语料切片、评测指标）；
5. **`platform/frontend/index.html`** — 单文件 SPA 六个视图与 API 契约的对应；
6. **编排与 CI** — 三个 Dockerfile + docker-compose.yml + ci.yml，重点看环境差异的显式声明（`ENGINE_RUN`/`KNOWLEDGE_DIR`）与语料三端一致；
7. **`docs/LLM_SETUP.md`** — 实接 DeepSeek 的三步配置与验证；
8. **`docs/RAG_KNOWLEDGE.md`** — 知识库语料本身（19 个自包含片段），兼作测试开发知识复习提纲。

## 测试思维声明

被测系统 mini-mall 中**有意注入了 5 个真实感缺陷**（水平越权、并发超卖、金额精度、参数校验缺失、分页静默错误），用于验证测试引擎的真实缺陷发现能力——7 条缺陷检测用例全部命中，且 CI 以"预期签名"持续守护这一事实。缺陷清单与设计文档见 `docs/BUGS.md`。
