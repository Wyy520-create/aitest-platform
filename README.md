# aitest-platform 智能接口测试平台

> 测试开发作品集项目：一个"自产自销"的全链路系统——**自己写被测系统、自己写测试引擎、自己搭测试平台、AI 辅助生成用例、CI 自动回归、公网可访问**。

## 项目组成

| 模块 | 说明 | 技术 |
|------|------|------|
| sut | 被测系统 mini-mall（迷你电商，含注入缺陷） | FastAPI + SQLAlchemy |
| engine | 分层接口自动化测试引擎 | Pytest + Requests |
| platform | 测试平台（用例管理/执行/报告） | FastAPI + Vue3 + MySQL |
| ai | LLM 生成用例 + RAG 系统质量评测 | DeepSeek API + Chroma |

## 架构图

```
浏览器 (Vue3 + Element Plus + ECharts)
        │  cpolar 公网访问
        ▼
平台后端 FastAPI ──────► MySQL（用例/执行记录/报告）
        │
        ├──► 执行引擎：动态起 Docker 容器
        │         └──► Pytest+Requests ──► 被测系统 mini-mall
        │                                  （测完销毁，环境永远干净）
        ├──► LLM 模块：接口文档 → 生成用例 → 人工评审入库
        └──► RAG 评测：6 类场景打分（幻觉率/注入成功率）
CI：GitHub Actions push 自动回归 + 质量门禁 badge
```

## 快速开始（M3 完成后一条命令）

```bash
git clone https://github.com/Wyy520-create/aitest-platform.git
cd aitest-platform
docker compose up -d
```

## 当前进度

- [x] M0-1 项目骨架
- [ ] M0 被测系统 mini-mall（用户/商品/购物车/订单 + 5 个注入缺陷）
- [ ] M1 Pytest 分层测试引擎
- [ ] M2 测试平台（后端+前端+动态容器执行）
- [ ] M3 Docker Compose 编排 + GitHub Actions CI + 公网上线
- [ ] M4 LLM 生成测试用例 + 人工评审流
- [ ] M5 RAG 问答系统 + 6 类场景质量评测

## 测试思维声明

被测系统 mini-mall 中**有意注入了若干真实感缺陷**（水平越权、并发超卖、金额精度、参数校验缺失等），用于验证测试引擎的真实缺陷发现能力。缺陷清单与设计文档见 `docs/BUGS.md`。
