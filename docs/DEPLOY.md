# 部署与演示指南

> 本文档回答两个问题：①从零部署运行，每个环节的细节（含 Windows 逐步步骤、Docker 启动关闭）；②如何通过 cpolar 把平台临时暴露到公网，让他人在自己的设备上直接访问。

---

## 1. 部署运行：需要什么、怎么做

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

### 1.4 5 分钟体验路线

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

## 2. 公网演示：cpolar 内网穿透

适用场景：远程协作时对方想在自己的设备上真实打开平台，或需要一个公网 URL 做展示。

### 2.1 一次性准备（每台电脑只做一次）

cpolar **必须配置 Authtoken 才能开隧道**（免费账号即可），它是识别你身份的凭证：

```bash
# ① 浏览器打开 https://www.cpolar.com 注册免费账号（邮箱即可）

# ② 登录后进后台「验证」页面，复制你的 Authtoken（一串字符）

# ③ 在要演示的电脑上执行（Authtoken 写入本机配置文件，一次即可）
cpolar authtoken 你的Authtoken粘贴在这里
```

**换电脑要不要重新配？要。** Authtoken 跟账号走，但配置写在本机文件里（Linux/macOS 是 `~/.cpolar/cpolar.yml`），新电脑上必须重新执行一次第 ③ 步。Windows/macOS 装客户端后，同样先在终端/PowerShell 执行一次 `cpolar authtoken xxx`。

### 2.2 开启隧道（2 分钟）

```bash
docker compose ps        # ① 确认三个容器都 Up
cpolar http 3000         # ② 前台运行，演示期间保持这个终端开着
```

输出示例：
```
Forwarding  https://a1b2c3d4.cpolar.io -> http://localhost:3000
```

把该链接发给对方或在会议中共享屏幕——任何人都能打开平台登录页。**验证技巧**：用自己的手机切 4G 打开链接，证明是真实公网访问而非局域网假象。

**免注册替代方案**：已装 Node 的话 `npx localtunnel --port 3000`，或有 cloudflared 的话 `cloudflared tunnel --url http://localhost:3000`，两条都无需注册。

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
# ① 终端前台短暂运行（Ctrl+C 关闭）——临时演示推荐这个，最直观
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

### 2.5 注意事项

- 免费版隧道**域名每次重启会变**——每次使用前现场生成
- 演示期间电脑**不能睡眠/断网**（系统设置临时关掉睡眠；后台运行的隧道休眠也会断）
- 用完收回：`Ctrl+C`（前台）/ `pkill cpolar`（后台）

---

*本文档只覆盖部署与演示；项目设计细节见 README「核心设计决策」。*
