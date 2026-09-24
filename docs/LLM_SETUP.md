# LLM 接入指南（AI 用例生成 / RAG 问答）

平台所有 AI 能力都做了**无 key 降级**：不配置任何密钥，整条链路依然可以完整演示
（用 MockLLM 规则模板替代大模型）。接真实 LLM 只是"换一个更好的生成器"，
业务代码零改动——这就是把 LLM 客户端抽象成接口的价值。

## 一、申请 DeepSeek API Key

1. 打开 https://platform.deepseek.com 注册
2. 左侧「API Keys」→ 创建 key，复制保存（只显示一次）
3. 充值 ¥10 够跑上千次生成（deepseek-chat 按 token 计费，一次生成约 1 分钱，适合项目演示）

## 二、配置方式

**方式 A：环境变量（推荐）**

```bash
export DEEPSEEK_API_KEY="sk-xxxxxxxx"
docker compose up -d --build
```

**方式 B：compose 环境变量文件**

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY=sk-xxxx
# .env 已在 .gitignore 中，不会被提交——密钥进 git 是安全红线
docker compose up -d
```

**方式 C：本地开发（不用 docker）**

```bash
export DEEPSEEK_API_KEY="sk-xxxxxxxx"
cd platform/backend && uvicorn app.main:app --port 8100
```

## 三、验证生效

平台「AI 工场」页面点"生成一批用例"：

- 未配 key：提示条显示 `[mock]`，用例名带 `[mock]` 前缀
- 已配 key：提示条显示 `[deepseek]`，用例名由模型自由命名，
  rationale 字段是模型的用例设计思路（比 mock 模板有价值得多）

## 四、相关代码导读

| 文件 | 职责 |
|---|---|
| `platform/backend/app/ai/llm.py` | LLM 客户端抽象：`RealLLM`(DeepSeek) + `MockLLM`(降级) + 工厂 `get_llm()` |
| `platform/backend/app/ai/case_generator.py` | 生成链路：拉 OpenAPI → 组 Prompt → 解析 → 存 draft |
| `platform/backend/app/config.py` | 环境变量读取（key/模型/基址都可覆盖） |

## 五、为什么选 DeepSeek

- OpenAI 兼容协议（`/v1/chat/completions`），换厂商只改 base_url
- 便宜，适合个人项目持续跑
- 中文测试用例命名质量好（用例名是中文，模型要理解中文语境）

**换其他厂商**（如通义/Kimi/本地 Ollama）只改两个环境变量：

```bash
DEEPSEEK_BASE_URL="https://api.moonshot.cn/v1"   # 任意 OpenAI 兼容端点
DEEPSEEK_MODEL="moonshot-v1-8k"
```

## 六、安全红线

- API key 永远只放环境变量 / .env（.gitignore 已排除）
- LLM 生成的用例一律进 `draft` 状态，**必须人工评审**后才会被执行——
  AI 产出不直接信任（untrusted output），这是 AI 测试工程的门禁原则
