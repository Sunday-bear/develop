# Roborock RAG — 扫地机器人 AI 客服

基于 RAG 技术的扫地机器人智能问答系统，数据源为 Roborock 官网产品说明书。

## 项目简介

爬取 Roborock 官网扫地机器人产品说明书 PDF → 转文本 → 向量化入库 → 构建 RAG 检索 → Streamlit 前端对话。

当前完成阶段：说明书爬虫模块 ✅

## 环境安装

```bash
# Python >= 3.10
pip install -r requirements.txt
```

## 项目目录

```
project/
├── project_root.py                 # 项目路径统一基准（唯一自算根目录）
├── config_loader.py                # 配置统一加载入口
├── main.py                         # 总调度入口
├── Dockerfile                      # 容器打包
├── .dockerignore                   # Docker 构建排除清单
├── requirements.txt                # 依赖清单（锁版本）
├── .gitignore                      # Git 忽略规则
├── .env                            # 敏感信息（不提交仓库）
├── README.md
│
├── config/                         # yaml 配置
│   ├── app.yaml                    # 全局公共配置
│   └── modules/                    # 各业务模块独立配置
│       └── manual_crawler.yaml
│
├── utils/                          # 全局公共工具
│   ├── __init__.py
│   └── logger.py                   # 日志工具（路径基 project_root）
│
├── src/                            # 业务模块
│   ├── __init__.py
│   └── manual_crawler/             # 说明书爬虫模块
│       ├── __init__.py
│       └── manual_crawler.py
│
├── data/                           # 原始数据（下载的 PDF）
├── output/                         # 中间产物
├── logs/                           # 日志
└── tests/                          # 单元测试（可选）
```

## 模块说明

| 模块 | 路径 | 职责 | 状态 |
|---|---|---|---|
| 说明书爬虫 | `src/manual_crawler/` | 爬取 Roborock API，下载扫地机器人说明书 PDF | ✅ |
| 日志工具 | `utils/logger.py` | 封装 logging，控制台+文件双输出，路径从 project_root 拼接 | ✅ |
| 配置加载 | `config_loader.py` | 统一读取 config/ 下全部 yaml + .env，不缓存敏感信息 | ✅ |
| 路径基准 | `project_root.py` | 以自身位置反推项目根目录，禁止硬编码 | ✅ |

## 模块单独自测

```bash
# 日志工具
python -m utils.logger

# 说明书爬虫（独立运行）
python -m src.manual_crawler.manual_crawler

# 配置加载器自测
python config_loader.py

# 路径基准自测
python project_root.py
```

## 完整项目运行

```bash
python main.py
```

## 容器启动

```bash
# 构建镜像
docker build -t roborock-rag .

# 运行（数据持久化，使用 volume 挂载）
docker run -v $(pwd)/data:/app/data -v $(pwd)/output:/app/output -v $(pwd)/logs:/app/logs roborock-rag
```

## 模块复用说明

每个业务模块放在 `src/` 下独立子目录，低耦合、单一职责：

- 可单独复制整个模块到其他项目使用
- 爬虫模块支持 `ManualCrawler(cfg=自定义字典)` 注入配置
- 不硬依赖全局 CONFIG，可脱离 config_loader 独立运行

## 环境变量说明

敏感信息通过 `.env` 管理（不提交代码仓库），按需在业务代码中用 `os.getenv("KEY")` 显式读取。

```bash
# .env 示例
# LLM_API_KEY=your_key_here
```

## Git 版本控制说明

项目初始化即启用 Git 版本控制，所有代码变更可追溯、可回退。

### 仓库初始化

```bash
# 本地仓库（已完成）
git init

# 关联远程 GitHub 仓库（替换为你的仓库地址）
git remote add origin https://github.com/<your-name>/roborock-rag.git
git branch -M main
git push -u origin main
```

### 提交规范（语义化）

| 前缀 | 含义 | 示例 |
|---|---|---|
| `feat:` | 新增功能 | `feat:新增PDF转文本模块` |
| `fix:` | 修复 Bug | `fix:修复爬虫重试次数失效` |
| `refactor:` | 重构代码 | `refactor:统一日志路径到project_root` |
| `docs:` | 更新文档 | `docs:新增Git版本控制章节` |
| `chore:` | 脚手架/配置调整 | `chore:新增Dockerfile和.dockerignore` |

### 标准提交流程

```bash
# 1. 修改代码后，先自测通过
python -m src.manual_crawler.manual_crawler

# 2. 查看变更
git status
git diff

# 3. 按模块拆分提交（不要一次性全 add）
git add src/manual_crawler/
git commit -m "refactor:爬虫模块按工程规范重构"

git add utils/
git commit -m "feat:新增日志工具模块"

# 4. 推送到远程
git push
```

### 版本回退

```bash
# 查看提交历史
git log --oneline

# 软回退（保留修改到暂存区）
git reset --soft HEAD~1

# 硬回退（丢弃未推送的修改，慎用）
git reset --hard <commit_hash>

# 回退某个文件到指定版本
git checkout <commit_hash> -- path/to/file.py
```

### AI 协作流程

每次 AI 生成/修改代码后：

```bash
# AI 生成代码 → 自测通过 → 提交当前版本
git add .
git commit -m "feat:xxx模块"

# 再进行下一轮 AI 修改 → 再自测 → 再提交
# 保证可随时回退到上一可用版本
```