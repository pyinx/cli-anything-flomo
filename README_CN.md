# cli-anything-flomo

[flomo](https://flomoapp.com/) 的生产级命令行工具。支持通过本地 IndexedDB 存储访问所有 memo，突破 API 的 500 条限制。

## 功能特性

- **Memo 管理**：创建、读取、更新、删除、筛选、置顶、归档 memo
- **本地数据访问**：从本地 IndexedDB 读取所有 memo（无 500 条限制！）
- **富文本支持**：保留粗体、斜体、下划线、高亮、列表、图片、链接
- **用户信息**：查看用户资料及 memo、标签统计
- **标签操作**：列表、搜索标签，支持层级显示
- **导出功能**：支持 JSON、Markdown、HTML、CSV、Obsidian 格式，保留富文本
- **JSON 输出**：所有命令支持 `--output json`，方便 AI Agent 调用
- **原生认证**：自动读取 flomo 桌面应用的凭证

## 安装

### 前置条件

1. **flomo 桌面应用**：必须已安装并登录（用于获取 API 认证凭证）
2. **dfindexeddb**：读取本地 IndexedDB 数据所需

```bash
pip install dfindexeddb
```

### 安装 CLI

```bash
cd agent-harness
pip install -e .
```

### 验证安装

```bash
cli-anything-flomo --help
# 或
python -m cli_anything.flomo.flomo_cli --help
```

### 认证方式

**无需手动配置凭证！** CLI 会自动从 flomo 桌面应用的配置文件中读取 `access_token`。

前提条件：
1. 已安装 [flomo 桌面应用](https://flomoapp.com/)
2. 在桌面应用中已登录账户

CLI 会自动从以下位置读取凭证：
- **macOS**：`~/Library/Containers/com.flomoapp.m/Data/Library/Application Support/flomo/config.json`
- **Windows**：`%APPDATA%/flomo/config.json`
- **Linux**：`~/.config/flomo/config.json`

> ⚠️ **注意**：如果你没有安装 flomo 桌面应用，CLI 将无法工作。flomo 官方不提供独立的 API Token 申请渠道，所有 API 访问都需要通过桌面应用的登录凭证。

---

## 使用方法

### 全局选项

```bash
--json         JSON 格式输出（用于 AI Agent）
--config PATH  指定 flomo config.json 路径
```

### 数据源选择

大多数列表命令支持 `--source` 参数：

```bash
--source local   # 从本地 IndexedDB 读取（默认，获取所有 memo）
--source api     # 从 API 读取（最多 500 条）
```

**推荐**：使用 `local`（默认）以获取完整数据。

### 输出格式

大多数列表命令支持 `--output` 参数：

```bash
--output string  # 人类可读文本（默认）
--output json    # JSON 格式，便于程序处理
```

---

## 命令参考

### 认证

```bash
# 查看认证状态
flomo auth status

# 测试 API 连接
flomo auth test
```

### 用户操作

```bash
# 显示用户资料
flomo user profile

# 显示用户统计（包含 memo 数量、标签分析）
flomo user stats
```

**输出包含**：
- 账户信息（ID、用户名、邮箱、会员状态）
- Memo 统计（总数、唯一标签数、内容长度）
- 最常用的 10 个标签

### Memo 操作

#### 列出 Memo

```bash
# 列出 memo（默认：10 条，来自本地 IndexedDB）
flomo memo list

# 带选项列出
flomo memo list --limit 20
flomo memo list --full          # 显示完整内容
flomo memo list --source api    # 使用 API 而非本地
flomo memo list -l 50 -f -s api # 组合选项
flomo memo list --output json   # JSON 输出
```

#### 创建 Memo

```bash
# 创建简单 memo
flomo memo create "来自 CLI 的问候"

# 带标签创建
flomo memo create "带标签的笔记" -t work -t important

# 标签自动转换为 #tag 格式
flomo memo create "我的笔记" -t "学习笔记/读书"
```

#### 获取 Memo

```bash
# 通过 slug 获取 memo
flomo memo get MjI0OTQwNDIx
```

#### 更新 Memo

```bash
flomo memo update <slug> --content "更新后的内容"
```

#### 删除 Memo

```bash
flomo memo delete <slug>
```

#### 按标签筛选

```bash
# 按标签筛选 memo（部分匹配）
flomo memo filter-tag "读书"
flomo memo filter-tag "学习" --limit 20
flomo memo filter-tag "读书" --source api
flomo memo filter-tag "读书" --output json
```

**注意**：`filter-tag` 使用部分匹配。搜索 "读书" 会匹配：
- `#学习笔记/读书/原则`
- `#学习笔记/读书/金钱的艺术`

#### 按内容筛选

```bash
# 按内容关键词筛选 memo
flomo memo filter-content "AI"
flomo memo filter-content "投资" --limit 30
flomo memo filter-content "AI" --source api
flomo memo filter-content "AI" --output json
```

#### 日期查询

```bash
# 今天的 memo（基于 created_at）
flomo memo today

# 最近 memo（默认：7 天）
flomo memo recent
flomo memo recent --days 14
flomo memo recent -d 30 -l 50
flomo memo recent --output json

# 按日期范围
flomo memo by-date 2024-01-01 2024-01-31
flomo memo by-date 2024-01-01 2024-01-31 --output json
```

#### 随机 Memo

```bash
# 获取一条随机 memo（用于灵感启发）
flomo memo random
flomo memo random --source api
flomo memo random --output json
```

#### 统计

```bash
# 显示 memo 统计（默认来自本地）
flomo memo stats
flomo memo stats --source api
flomo memo stats --output json
```

#### 置顶操作

```bash
# 列出置顶 memo
flomo memo pinned

# 置顶 memo
flomo memo pin <slug>

# 取消置顶
flomo memo unpin <slug>
```

#### 归档操作

```bash
# 列出归档 memo
flomo memo archived

# 归档 memo
flomo memo archive <slug>

# 取消归档
flomo memo unarchive <slug>
```

#### 回收站操作

```bash
# 列出已删除 memo
flomo memo trash

# 从回收站恢复 memo
flomo memo restore <slug>
```

**注意**：回收站中的 memo 仅通过 API 可用，本地存储无法访问。

### 标签操作

#### 列出标签

```bash
# 列出所有标签（默认：10 条，来自本地 IndexedDB）
flomo tag list

# 带选项列出
flomo tag list --limit 50
flomo tag list --output tree    # 树形格式显示
flomo tag list --search "读书"  # 按关键词筛选
flomo tag list --source api     # 使用 API 而非本地
flomo tag list --output json    # JSON 输出
```

#### 搜索标签

```bash
# 按关键词搜索标签（部分匹配，不区分大小写）
flomo tag search "读书"
flomo tag search "学习" --limit 20
flomo tag search "读书" --output json
```

#### 标签统计

```bash
flomo tag stats
flomo tag stats --output json
```

### 导出操作

导出命令支持多种格式和数据源：

```bash
# 导出为 JSON（默认）
flomo export run
flomo export run --output memos.json
flomo export run -f json -o memos.json

# 导出为 Markdown
flomo export run --format markdown --output memos.md
flomo export run -f markdown -o memos.md

# 导出为 HTML
flomo export run --format html --output memos.html

# 导出为 CSV
flomo export run --format csv --output memos.csv

# 导出为 Obsidian 格式（带 YAML frontmatter 的 Markdown）
flomo export run --format obsidian --output notes.md

# 从 API 导出而非本地
flomo export run -f json -o memos.json --source api

# 导出到目录（自动生成文件名）
flomo export run -f markdown -d ~/exports
flomo export run -f obsidian -d ~/notes
```

**支持的格式**：
- `json`：memo 对象的 JSON 数组（保留原始 HTML 内容）
- `markdown`：人类可读的 Markdown，富文本从 HTML 转换
- `html`：带样式的 HTML 页面（保留原始格式）
- `csv`：兼容电子表格的 CSV（纯文本）
- `obsidian`：兼容 Obsidian 的 Markdown，带 YAML frontmatter 和 wiki 风格链接

**富文本支持**：

导出为 Markdown 或 Obsidian 格式时，保留以下 flomo 格式：

| flomo 格式 | HTML | Markdown 输出 |
|------------|------|---------------|
| 粗体 | `<strong>`, `<b>` | `**粗体**` |
| 斜体 | `<em>`, `<i>` | `*斜体*` |
| 高亮 | `<mark>` | `==高亮==` |
| 下划线 | `<u>` | `<u>下划线</u>` (HTML) |
| 删除线 | `<s>`, `<del>` | `~~删除线~~` |
| 无序列表 | `<ul><li>` | `- 列表项` |
| 有序列表 | `<ol><li>` | `1. 列表项` |
| 链接 | `<a href>` | `[文本](url)` |
| 图片 | `<img src>` | `![alt](url)` |
| 代码 | `<code>` | `` `代码` `` |
| 引用 | `<blockquote>` | `> 引用` |
| 双向链接 (@) | `<a href="flomo://memo/...">` | `[[笔记名]]` (Obsidian) |

**双向链接支持**：

导出为 Obsidian 格式时，flomo 的 @ 双向链接自动转换为 Obsidian 的 wikilink 格式：

- `@笔记名` → `[[笔记名]]`
- `<a href="flomo://memo/ABC123">@关联笔记</a>` → `[[关联笔记]]`
- 带 `data-memo-slug` 属性的链接 → `[[slug]]`

这样可以直接与 Obsidian 的笔记链接系统无缝集成，在 Obsidian 中直接导航到关联笔记。

**注意**：HTML 导出保留所有原始格式。CSV 导出会移除格式以获得纯文本。

---

## JSON 输出（用于 AI Agent）

所有命令支持 `--output json` 标志，输出机器可读格式：

```bash
flomo --json memo list
flomo memo list --output json
flomo memo filter-tag "读书" --output json
flomo tag list --output json
flomo memo stats --output json
```

---

## 命令汇总

| 命令 | 默认限制 | 默认来源 | 关键选项 |
|------|----------|----------|----------|
| `memo list` | 10 | local | `-f` 完整内容, `-o json` |
| `memo filter-tag` | 100 | local | 部分匹配, `-o json` |
| `memo filter-content` | 100 | local | 关键词搜索, `-o json` |
| `memo today` | 100 | local | 基于 created_at |
| `memo recent` | 100 | local | `-d` 天数, `-o json` |
| `memo by-date` | 200 | local | 日期范围查询 |
| `memo random` | 200 | local | 随机选择 |
| `memo stats` | 500 | local | 统计信息, `-o json` |
| `memo trash` | 10 | api | 仅 API |
| `memo archived` | 200 | api | 仅 API |
| `memo pinned` | - | api | 仅 API |
| `tag list` | 10 | local | `-o tree` 层级显示 |
| `tag search` | 10 | local | 部分匹配 |
| `tag stats` | - | local | 使用统计 |
| `export run` | 500 | local | `-f` 格式, `-d` 目录 |

---

## 开发

### 项目结构

```
agent-harness/
├── FLOMO.md              # 软件特定 SOP
├── setup.py              # PyPI 包配置
├── README.md             # 英文文档
├── README_CN.md          # 中文文档（本文件）
└── cli_anything/         # 命名空间包（无 __init__.py）
    └── flomo/            # 子包
        ├── __init__.py
        ├── flomo_cli.py  # 主 CLI 入口
        ├── core/         # 业务逻辑
        │   ├── auth.py
        │   ├── memo.py
        │   ├── tag.py
        │   ├── user.py
        │   └── export.py
        ├── utils/        # 工具函数
        │   ├── api.py    # 带签名的 API 客户端
        │   ├── config.py # 配置管理
        │   ├── idb_reader.py # IndexedDB 读取器
        │   └── output.py # 输出格式化
        └── tests/
            ├── TEST.md
            ├── test_core.py
            └── test_full_e2e.py
```

### 运行测试

```bash
cd agent-harness
pytest cli_anything/flomo/tests/ -v
```

### 关键实现细节

1. **API 请求签名**：所有 API 请求包含 MD5 签名和盐值
2. **分页**：`get_all_memos()` 通过基于游标的分页突破 500 条限制
3. **IndexedDB**：使用 `dfindexeddb` 读取本地 Electron/LevelDB 存储
4. **标签筛选**：支持层级标签的部分匹配（如 "读书" 匹配 `#学习笔记/读书/原则`）

## API 参考

CLI 使用 flomo 的 REST API：

- **基础 URL**：`https://flomoapp.com/api/v1/`
- **认证**：从原生应用配置读取 Bearer token
- **签名**：排序参数 + 盐值的 MD5 哈希

## 许可证

MIT License
