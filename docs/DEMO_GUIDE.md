# 部署演示指南（面试官 / 零基础友好版）

> 本文档回答五个问题：①这个项目是什么、3 分钟怎么讲明白；②从零部署运行，每个环节的细节（含 Windows 傻瓜式步骤、Docker 启动关闭）；③面试现场怎么用 cpolar 公网演示（含后台常驻）；④技术面高频问题怎么答；⑤"印象最深的 bug"怎么答。

---

## 0. 这个项目是什么（3 分钟讲法）

### 30 秒电梯版（任何时候都能脱口而出）

"aitest-platform 是一个智能接口测试平台：一个带 7 个真实缺陷的电商系统 mini-mall 作为被测对象，平台对它跑 45 条自动化接口用例、命中全部 7 个缺陷，外加两个 AI 能力——AI 用例生成（人工评审后才入库）和 RAG 知识问答（自实现检索 + 拒答保护）。全套 docker 一键启动，GitHub Actions 自动回归，clone 下来 10 分钟就能跑通。"

### 3 分钟面试版（三段式：是什么 → 能做什么 → 怎么做到的）

**第 1 分钟 · 是什么：**
"项目分两部分。**被测系统 mini-mall** 是我开发的一个电商后端 API，故意埋了 7 个真实缺陷——水平越权、库存超卖、金额精度、分页边界这些线上典型事故类型。**测试平台**围绕它搭建：45 条 Pytest 分层自动化用例、Vue3 + Element Plus 前端加 FastAPI 后端、两个 AI 模块（用例生成和知识库问答），全部容器化，三条 CI 作业自动回归。"

**第 2 分钟 · 能做什么（数字 + 演示路径）：**
"45 条用例命中全部 7 个缺陷；RAG 评测集 21 条、MRR 0.972，进了 CI 防回归；CI 三条作业 88 秒跑完。现场演示 5 分钟：执行中心一键跑套件，7 个失败用例每个都带缺陷定位说明；AI 工场从被测系统接口文档自动生成用例草稿，走人工评审门禁；RAG 问答演示正常回答和无关问题拒答。"

**第 3 分钟 · 怎么做到的（三个技术决策）：**
"一、执行层数据驱动，用例只存相对路径，被测系统地址是唯一环境变量 `SUT_BASE_URL`——换系统不改代码；二、AI 生成不直接入库，必须人工评审——LLM 会幻觉，产出不直接信任，而且采纳率本身成为质量度量；三、RAG 拒答阈值用'得分率'而不是 BM25 绝对分——绝对分和查询长度正相关，短查询会被误杀，阈值 0.055 是跑全量数据看分布定出来的。每个决策的踩坑过程都写在代码注释和 git 历史里。"

---

## 1. 部署运行：需要什么、怎么做（细节全在这）

### 1.1 装 Docker（唯一前置）

| 系统 | 做法 |
|---|---|
| Windows 10/11 | 官网下载 **Docker Desktop for Windows** 安装包，双击安装（会自动启用 WSL2，装完按提示重启电脑）。内存建议 4GB+ |
| macOS | 官网下载 **Docker Desktop for Mac**（Apple 芯片选 Apple Silicon 版），拖进 Applications |
| Linux（Debian/Ubuntu） | 终端执行：`sudo apt install docker.io docker-compose-v2` |

**Linux 装完还有四步（漏了必踩坑）：**

```bash
# ① 启动 Docker 服务（安装时一般已启动，这条保稳 + 设置开机自启）
sudo systemctl enable --now docker

# ② 让当前用户免 sudo 用 docker（不配的话每条 docker 命令都要加 sudo）
sudo usermod -aG docker $USER

# ③ 重新登录终端（关闭终端重开，或注销重登）——用户组改动必须重新登录才生效！

# ④ 验证安装成功（打印 "Hello from Docker!" 即成功）
docker run hello-world
```

**Docker 本身的启动 / 关闭**：Windows/macOS——Docker Desktop 就是普通软件，双击启动、右键鲸鱼图标 Quit 关闭（建议设置里勾选 "Start Docker Desktop when you sign in" 开机自启）；Linux——`sudo systemctl start docker` / `sudo systemctl stop docker`。日常只是暂停/继续项目，不动 Docker 本身，用 1.6 的 compose 命令管项目容器就够了。

### 1.2 一键部署（macOS / Linux，4 条命令）

```bash
# ① 克隆仓库（公开仓库，无需任何凭据）
git clone https://github.com/Wyy520-create/aitest-platform.git
cd aitest-platform

# ② 创建环境配置文件（管理员密码 / LLM key 都在这里，默认即可跑）
cp .env.example .env

# ③ 构建并启动全栈（首次约 2~5 分钟；之后每次启动只要几秒）
docker compose up -d --build

# ④ 等约 10 秒让后端就绪，打开浏览器访问 http://localhost:3000
```

**验证成功的标志**：出现登录页 → 输入 `admin` / `admin123` → 进入"看板"页看到统计图表。

### 1.3 Windows 从零开始（每步点哪里都写明）

**第 1 步 · 装并启动 Docker Desktop**
① 浏览器打开 `docker.com/products/docker-desktop` → 下载 Docker Desktop for Windows → 双击安装 → 按提示重启电脑；
② 双击桌面 **Docker Desktop** 图标启动，等窗口左下角鲸鱼图标变绿（首次启动要 1~2 分钟初始化）。

**第 2 步 · 打开 PowerShell**
按 `Win` 键 → 输入 `powershell` → 回车（黑蓝色窗口就是终端）。

**第 3 步 · 验证 Docker 可用**
```powershell
docker run hello-world
```
打印 `Hello from Docker!` 即成功。报错 "error during connect" 就是 Docker Desktop 没启动或没绿，回第 1 步②。

**第 4 步 · 拉取项目**
```powershell
cd $env:USERPROFILE\Desktop        # 项目放桌面，想换位置改这里
git clone https://github.com/Wyy520-create/aitest-platform.git
cd aitest-platform
```
（电脑没装 Git：浏览器打开 `https://github.com/Wyy520-create/aitest-platform` → 绿色 Code 按钮 → Download ZIP → 解压到桌面 → 解压后的目录里按住 Shift 右键空白处 → "在此处打开 PowerShell 窗口"，然后继续第 5 步。）

**第 5 步 · 创建配置文件**
```powershell
Copy-Item .env.example .env
```
⚠️ 如果改用记事本手工建：保存时"保存类型"必须选**所有文件**，文件名就是 `.env`——否则会变成 `.env.txt`，平台读不到配置。

**第 6 步 · 启动全栈**
```powershell
docker compose up -d --build
```
首次约 2~5 分钟，看到 `Container aitest-platform-xxx Started` ×3 即完成。

**第 7 步 · 可视化确认（不会命令行也能看）**
打开 Docker Desktop 窗口 → 上方 **Containers** 页签 → 看到 `aitest-platform` 一组三个容器都是绿色 **Running**。

**第 8 步 · 打开平台**
浏览器访问 `http://localhost:3000` → 账号 `admin` / 密码 `admin123` → 进入看板即成功。

**Windows 常见报错对照**：
| 报错 | 原因 |
|---|---|
| `error during connect ... dockerDesktopLinuxEngine` | Docker Desktop 没启动，等鲸鱼变绿 |
| 端口 3000 被占 | 改 `docker-compose.yml` 的 `"3000:80"` 为 `"3001:80"` 再 `up -d`，访问 3001 |
| 改了 .env 没反应 | `docker compose up -d --force-recreate backend`（环境变量启动时才读入） |
| 想从头重来 | `docker compose down -v` 后重新 `up -d --build`（数据卷也删，完全重置） |

### 1.4 5 分钟体验路线（面试官跟着点一遍就懂）

1. **看板**：通过率趋势、模块分布、统计卡片
2. **执行中心 → 点"执行测试"**：约 10 秒出报告，**7 个 failed 就是被测系统埋的 7 个真实缺陷**；点失败行看缺陷定位（如"page=0 应报错却返回 200"）
3. **用例管理**：45 条用例按模块筛选，点用例看请求构造与断言
4. **AI 工场 → 生成一批用例**：从被测系统接口文档自动生成草稿 → 逐条"采纳/驳回"写理由 → 右上角采纳率变化
5. **RAG 问答**：点快捷问题（2 回答 + 1 拒答），手动输"秒杀为什么超卖"，点"跑质量评测"看 21 条全绿

### 1.5 卡住怎么办（通用排查表）

| 症状 | 原因与解决 |
|---|---|
| `localhost:3000` 打不开 | `docker compose ps` 看三个容器是否都 Up；等 10 秒再刷 |
| 登录报 500 / 一直转圈 | 后端还在启动，等 10 秒；或 `docker compose logs backend` 看报错 |
| `docker compose` 报权限错误（Linux） | 1.1 的第 ②③ 步没做：加 docker 用户组 + 重新登录终端 |
| `docker compose` 命令不存在 | 老版本 Docker 用 `docker-compose`（中间有连字符） |
| 端口被占（3000/8000/8100） | 改 `docker-compose.yml` 的 `ports:` 映射，再 `up -d` |
| 改了 .env 不生效 | 环境变量容器启动时才注入：`docker compose up -d --force-recreate backend` |
| 看日志 | `docker compose logs -f backend`（平台后端）/ `sut`（被测系统） |

### 1.6 命令速查（启动/关闭/重置）

```bash
docker compose ps                 # 查看容器状态
docker compose up -d              # 启动平台（日常用这个，秒级）
docker compose down               # 停止并删除容器（数据保留，下次 up 接着用）
docker compose down -v            # 连数据库卷一起删 = 完全重置，下次启动重新建库
docker compose logs -f backend    # 跟踪后端日志
```

---

## 2. 面试现场：cpolar 公网演示

适用场景：线上面试共享屏幕 / 面试官想在自己设备上真实点开平台。

### 2.1 一次性准备（每台电脑只做一次）

cpolar **必须配置 Authtoken 才能开隧道**（免费账号即可），它是识别你身份的凭证：

```bash
# ① 浏览器打开 https://www.cpolar.com 注册免费账号（邮箱即可）

# ② 登录后进后台「验证」页面，复制你的 Authtoken（一串字符）

# ③ 在要演示的电脑上执行（Authtoken 写入本机配置文件，一次即可）
cpolar authtoken 你的Authtoken粘贴在这里
```

**换电脑要不要重新配？要。** Authtoken 跟账号走，但配置写在本机文件里（Linux/macOS 是 `~/.cpolar/cpolar.yml`），新电脑上必须重新执行一次第 ③ 步。Windows/macOS 装客户端后，同样先在终端/PowerShell 执行一次 `cpolar authtoken xxx`。

### 2.2 演示步骤（演示前 2 分钟）

```bash
docker compose ps        # ① 确认三个容器都 Up
cpolar http 3000         # ② 前台运行，演示期间保持这个终端开着
```

输出示例：
```
Forwarding  https://a1b2c3d4.cpolar.io -> http://localhost:3000
```

把该链接发给面试官/投屏——任何人都能打开平台登录页。**进阶秀法**：自己手机 4G 打开链接，证明真实公网可访问。

**兜底方案**（面试官不想注册 cpolar 时）：已装 Node 的话 `npx localtunnel --port 3000`，或有 cloudflared 的话 `cloudflared tunnel --url http://localhost:3000`，两条都无需注册。

### 2.3 查看公网地址：cpolar 本地管理页（9200 端口）

**9200 管理页由 cpolar 进程常驻提供**——不管用哪种方式启动（前台 / daemon 后台 / systemctl 服务），只要 cpolar 进程活着就能访问。这也是 `systemctl enable --now cpolar` 启动后立刻能开 9200 的原因：

- **浏览器直接访问 `http://localhost:9200`**——首次打开输入你的 Authtoken 登录；左侧 "在线隧道列表" 里能看到当前隧道的公网 URL（还能看请求统计）。没有在线隧道时列表为空，但页面照常可用
- 命令行取公网地址（适合脚本里用）：
  ```bash
  curl -s http://localhost:9200/api/tunnels
  ```

### 2.4 短暂运行 vs 长期后台运行（按系统对照）

`cpolar http 3000` 是前台进程，Ctrl+C / 关终端就断。各系统的"短暂运行"和"后台常驻"写法：

**Linux / macOS：**
```bash
# ① 终端前台短暂运行（Ctrl+C 关闭）——面试演示推荐这个，最直观
cpolar http 3000

# ② cpolar 原生后台运行（-daemon=on，关掉终端仍存活，关机/休眠才断）
cpolar http 3000 -daemon=on
# 关闭后台：pkill cpolar

# ③ 注册为系统服务（官方安装脚本自带 cpolar.service，开机自启、崩溃自恢复）
sudo systemctl enable --now cpolar
# 注意：服务方式默认跑配置文件（~/.cpolar/cpolar.yml）里定义的隧道；
# 配置里没有隧道时，启动后只有 9200 管理页、没有指向 3000 的隧道。
# 要常驻 3000 隧道，先按 ② 的 daemon 方式跑，或把隧道写进配置文件再启用服务。
# 停止服务：sudo systemctl stop cpolar
```

**Windows（PowerShell）：**
```powershell
# ① 终端前台短暂运行（Ctrl+C 关闭）
cpolar http 3000

# ② 后台长期运行（启动后命令立即返回，不占用终端）
Start-Process cpolar -ArgumentList "http","3000"

# 关闭后台进程
Get-Process cpolar | Stop-Process        # PowerShell 的 pkill 等价写法
# 或者在任务管理器里结束 cpolar.exe
```

后台/服务运行时查公网地址，用 2.3 的 `localhost:9200` 管理页即可，不用翻终端日志。

### 2.5 现场话术（cpolar 与公司正式部署的对应）

> "本地演示我用 cpolar 做临时内网穿透，把本机 3000 端口暴露到公网。**正式部署时这套 docker-compose 原样搬到公司服务器**——compose 编排、服务拓扑、CI/CD 全部不变，唯一变化是把临时隧道换成服务器上 nginx 直接监听 80/443，再挂域名和 HTTPS 证书。容器化的意义就在于此：环境一致性不依赖任何特定机器，换一台装了 Docker 的主机，一条 `docker compose up -d` 就上线。"

### 2.6 注意事项

- 免费版隧道**域名每次重启会变**——现场生成现场用，别提前写进简历
- 演示期间电脑**不能睡眠/断网**（系统设置临时关掉睡眠；后台运行的隧道休眠也会断）
- 演示完收回：`Ctrl+C`（前台）/ `pkill cpolar`（后台）

---

## 3. 技术面高频问答（FAQ）

> 原则：先一句话答"是什么"，再一句"为什么/怎么做的"，最后主动给一个数字或细节。宁短勿长，给面试官追问空间。

**Q1：RAG 问答是什么？你的实现方案？**
检索增强生成：问题先检索知识库拿到相关片段，再让 LLM 基于片段作答，避免幻觉。我的实现：中文 bigram 分词 → 自实现 BM25 检索（lru_cache 建索引）→ 得分率低于阈值拒答 → 有 LLM key 用 DeepSeek 润色、无 key 规则直出。质量用 21 条 7 类评测集（hit@3 / MRR / 拒答率）度量，进 CI 防回归。

**Q2：为什么自实现 BM25，不用 Chroma/FAISS 向量检索？**
三个理由：①教学价值——检索是 RAG 的核心，黑盒调库学不到东西，BM25 两百行就能看清 IDF、长度归一化的每个细节；②依赖最小——评测器零第三方依赖，CI 永远不可能因为向量库版本漂移挂掉；③对这个域足够——几千字的技术文档，词项匹配比语义向量更可控、可解释。向量检索是已评估过的备选，语料到百万字级再上。

**Q3：拒答阈值怎么定的？**
不是拍的。实测发现 BM25 绝对分和查询长度正相关——8 字口语查询和拒答类问题分数完全重叠，绝对阈值无解。于是归一化成"得分率 = 实际分 / 该查询理论满分"，再跑全部用例看分布：拒答类 ≤0.046、正常类 ≥0.070，阈值取分离带中间 0.055，两侧各留余量。并把当初误杀的查询补进评测集防回归。

**Q4：CI/CD 流水线怎么配置的？**
GitHub Actions 单文件三 job：`api-tests`（compose 起全栈，容器内跑 45 条用例并断言签名 45/38/7/7）、`platform-e2e`（HTTP 闭环：登录→触发执行→断言统计）、`rag-eval`（21 条检索质量评测）。push 到 master 触发，全绿约 88 秒，README badge 实时显示。

**Q5：为什么 CI 断言"45/38/7/7"而不是断言全绿？**
这是我故意设计的"预期签名"。被测系统的 7 个缺陷是资产——如果哪天有人"修好"一个缺陷，或套件被改坏导致抓不到缺陷，测试数、通过数、失败数、命中缺陷数会一起变化，CI 立即挂红。**测试平台必须能证明自己的测试是有效的**，全绿断言反而证明不了。

**Q6：AI 生成的用例为什么要人工评审才入库？**
LLM 会幻觉：可能生成不存在的接口、错误的预期状态码。直接入库会把垃圾用例混进回归套件，失败信号就不可信了。所以平台设计是 AI 只产 draft，人审通过（reviewed）才进可执行套件，拒绝的留档可分析——这样"AI 采纳率"本身也成为质量度量（度量 AI 而不只是使用 AI）。

**Q7：没配大模型 key，AI 功能怎么演示？成本怎么控制？**
LLM 访问做了抽象：有 key 走 DeepSeek 真实调用，无 key 自动降级 MockLLM（规则模板），整条链路（生成→评审→入库→执行→统计）照常可演示。设计上 CI 只断言检索层确定性指标、永不调 LLM，自动化回归零 AI 成本；真实 key 走环境变量注入，不进 git。

**Q8：45 条用例的设计思路？**
按四类测试设计方法系统化覆盖：正向功能（冒烟）、边界值（长度/数值/分页边界）、异常参数（类型错/缺失/非法值）、安全（水平越权/未授权）。每条用例对应一个缺陷检测点，独立用户、数据隔离防 flaky。

**Q9：并发超卖这种并发缺陷怎么自动化验证？**
多线程并发请求同一个秒杀接口 N 次，然后断言库存扣减次数与成功订单数一致——成功下单数 ≤ 库存量、库存不能为负。代码里是 `concurrent.futures` 起 10 个线程同时下单，再查库存与订单，暴露竞态。

**Q10：数据库为什么用 SQLite？**
MVP 取舍：单容器自足、零运维、clone 即跑，对演示和测试平台的量级绰绰有余。数据层走 SQLAlchemy ORM，切 MySQL/PostgreSQL 只改连接串，模型代码零改动——这是抽象层的意义。

**Q11：前端为什么用 CDN 单文件而不用 Vue 脚手架工程？**
刻意的教学与演示取舍：一个 index.html 零构建、零 node_modules，面试官打开文件就能读懂全链路（模板→响应式→API 调用），docker 镜像也极简（nginx + 单文件）。代价是踩了 in-DOM 模板与 Element Plus 的兼容坑（见第 4 章备用故事），已修复并注释。

**Q12：密码和密钥安全怎么处理的？**
三层：①密码 pbkdf2 加盐慢哈希存储，登录比较用 compare_digest 防时序攻击，JWT 鉴权；②真实 API key 只存在部署机 .env（gitignore 排除，仓库与 git 历史零密钥），公开仓库只有空占位符；③compose 内部网络隔离，被测系统的数据工厂接口不暴露到宿主机。

**Q13：怎么保证用例之间不互相污染（防 flaky）？**
每个用例动态注册独立用户（随机用户名）、独立 token、独立造数，执行顺序无关；断言只依赖自己创建的数据。平台执行同样按用例隔离 token。

**Q14：换被测系统怎么弄？**
平台与被测系统只有一个耦合点：环境变量 `SUT_BASE_URL`。换外部系统改它即可；如果被测系统也有容器，直接换掉 compose 里 sut 服务的镜像、服务名不变，平台配置零改动。AI 工场会从新系统的 OpenAPI 文档自动生成初版用例。已知边界：登录态预取按当前系统的认证契约实现，换认证方式要适配——抽象成可插拔认证器是演进方向。

**Q15：如果继续迭代，下一步做什么？**
按价值排序：①SUT 管理页——把被测系统从环境变量提升为平台资源，支持一套用例打多套环境并行回归；②测试报告导出（HTML/PDF）与定时执行；③RAG 语料管理界面。每个的改动面都已经评估过，是明确的技术路线而不是泛泛而谈。

---

## 4. 面试弹药：印象最深的 bug（STAR 讲法）

被问这个问题时，**讲排障过程比讲 bug 本身值钱**。每个故事按"情境 → 行动 → 结果"组织，30~60 秒一个。

### 故事一：推送后 CI 完全没有运行（配置类问题的排障方法论）

- **情境**：代码推上 GitHub 后，Actions 页面空空如也，workflows API 返回 0 条记录——不是失败，是根本没被触发。
- **行动**：按判别顺序排查：先确认 workflow 文件在远端存在（raw URL 能访问）→ 再用知名公开仓（actions/checkout）做**匿名 API 对照实验**，排除"查询方式不对"的误判 → 最后通读配置发现触发条件写的是 `branches: [main]`，而仓库默认分支是 `master`——事件从未匹配，GitHub 根本没注册这个 workflow。
- **结果**：改成 `[master, main]` 推送后 CI 立即激活，三作业 88 秒全绿。教训：**"文件在但行为没发生"时，先看触发条件与真实环境是否匹配**；对照实验能快速隔离"配置错"还是"平台怪"。

> 加分句：CI 不报错也不运行，没有任何错误信息可抓，考验的是排障方法而不是工具熟练度。

### 故事二：RAG 把正常问题误判拒答（算法理解 + 数据驱动决策）

- **情境**：知识库问答里"秒杀为什么超卖"被判为"知识库无相关内容"拒答，但语料明明有对应文档。本地评测集 18 条全过，它是个漏网之鱼。
- **行动**：先排除语料缺失 → 写探查脚本跑全部评测用例的分数，发现根因：**BM25 绝对分与查询长度正相关**，拒答类最高 4.08 分与正常短查询 2.71~4.11 分完全重叠，绝对阈值无解 → 归一化为"得分率 = 实际分 / 该查询理论满分" → 实测分布出现分离带 [0.046, 0.070]，阈值取中间 0.055。
- **结果**：误拒修复；把漏网查询补进评测集第 7 类"口语化短查询"防回归，评测集扩到 21 条，本地/容器/CI 三端指标一致。

> 加分句：没有拍阈值上线，先跑数据看分布，让数据决定——测试思维反哺算法调优。

### 故事三：同一份评测集，容器里分数比本地低（测试环境治理）

- **情境**：同代码同评测集，容器 MRR 0.963、本地 0.972——**评测结果不可比**，CI 断言没法写。
- **行动**：逐文件比对容器与本地语料，发现 Dockerfile 多拷了一份 README.md——README 是导航文档，每个 chunk 重复各模块名，干扰相关度排序，5 个 chunk 就改变了 MRR。
- **结果**：确立语料治理规则并写进代码注释：**只有"稳定 + 自包含"的文档才进检索语料**；修复后三端指标一致。教训：评测输入的任何环境差异都会让指标漂移——**先治理测试环境，再谈优化指标**。

### 备用故事：前端表格"表头在、数据空"（实测抓 bug）

- **情境**：浏览器实测发现草稿表格 ID/用例名/模块三列只有表头没有数据，接口返回明明正常。
- **行动**：浏览器工具直接抓 DOM，prop 简写列表头渲染了但数据单元格缺失，带 template 的列正常——定位为**无构建单文件（in-DOM 模板）下 Element Plus 的兼容差异**。
- **结果**：全站 11 处统一改显式插槽，坑写进代码注释。教训：**浏览器实测比接口自测多覆盖一层渲染层**，UI bug 只有真打开页面才现形。

---

*最后更新：2026-09-24 · 与仓库 README 的快速开始互为摘要与详版*
