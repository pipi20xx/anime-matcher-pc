# Anime-Matcher PC (专业级剧集整理工具)

基于 [anime-matcher](https://github.com/pipi20xx/anime-matcher) 核心算法的桌面端重命名与整理工具。本项目采用解耦的组件化架构，集成本地 AI 识别、云端元数据对撞及高度自定义的规则引擎。

## ✨ 核心特性

- **模块化架构**：UI 容器与业务页签 (Main/Settings/Rules) 完全解耦，代码清晰易维护。
- **全自动识别 (L1 + L2)**：
    - **内核识别 (L1)**：精准提取文件名中的标题、集数、制作组等原始元数据。
    - **云端对撞 (L2)**：联动 **TMDB** 与 **Bangumi**，自动补全官方标题、上映年份、评分及制片国家。
- **规则管理中心**：
    - **多维度过滤**：独立配置屏蔽词 (Noise)、制作组 (Groups)、特权规则 (Privileged) 及渲染规则 (Render)。
    - **远程同步**：支持从 GitHub 等地址一键同步并本地缓存远程规则。
    - **高性能存储**：采用 **SQLite (Peewee ORM)** 存储规则与指纹记忆，加载速度极快。
- **智能重命名引擎**：
    - **全字段支持**：基于 JSON 配置的 22 个元数据字段（如 `{team}`, `{resolution}`, `{season_02}`, `{video_encode}` 等）。
    - **路径自动记忆**：自动创建主文件夹与季文件夹，支持自定义偏移与媒体类型覆盖。
- **用户体验优化**：
    - **深度拖拽支持**：自动解码 URL 编码，支持直接拖入文件或整个文件夹。
    - **状态记忆**：自动记忆窗口尺寸、位置及界面分割条比例。
    - **EXE 友好**：内置统一路径管理器，支持 PyInstaller 一键打包。

## 🏗️ 目录结构

```text
/
├── main.py                 # 程序启动入口
├── VideoRenamer_Qt6.ini    # 用户配置 (自动生成)
├── VideoRenamer.db         # 本地规则数据库 (自动生成)
├── data/                   # 核心算法生成的缓存目录 (自动生成)
│   └── matcher_storage.db  # 核心元数据缓存与指纹记忆
├── anime-matcher-main/     # 核心算法库 (外部导入/自动下载)
└── src/
    ├── gui/                # UI 层
    │   ├── tabs/           # 解耦的页签组件 (MainTab, SettingsTab)
    │   ├── rule_manager.py # 规则管理组件
    │   └── worker.py       # 异步处理线程 (QThread)
    ├── core/               # 业务逻辑层
    │   ├── processor.py    # 算法适配器 (L1/L2 联动逻辑)
    │   ├── renamer.py      # 重命名执行引擎
    │   └── rules.py        # 规则合并与同步逻辑
    └── utils/              # 工具层
        ├── paths.py        # 统一路径管理器 (适配开发与打包环境)
        ├── config.py       # QSettings 配置管理
        ├── database.py     # SQLite/Peewee ORM 模型
        └── placeholders.json # 占位符定义字典
```

## 🚀 快速上手

### 1. 环境准备
确保安装 Python 3.10+，并执行依赖安装：
```bash
pip install PyQt6 requests regex peewee
```

### 2. 初始化核心
启动程序后，前往 **“设置与算法”** 页签：
- 点击 **“自动下载/更新 (GitHub)”** 部署识别内核。
- 填入你的 **TMDB API Key** 并配置网络代理（如在国内环境运行）。

### 3. 配置规则
前往 **“识别规则管理”**：
- 在左侧输入本地自定义的过滤词。
- 在右侧填入远程订阅 URL 并点击同步。

### 4. 开始整理
回到 **“主界面”**，拖入视频文件，点击 **“预览重命名”**，确认无误后点击 **“执行重命名”**。

## 📦 打包 EXE
本项目已完成打包适配，使用 PyInstaller 即可生成单文件或文件夹版本：
```bash
pyinstaller --noconfirm --onedir --windowed ^
  --add-data "src/utils/placeholders.json;src/utils" ^
  --name "AnimeProRenamer" ^
  main.py
```

## 📜 占位符参考
程序内置了详尽的占位符帮助文档，可在设置页面点击 **“💡 占位符说明”** 查看并复制代码。常见占位符包括：
- `{title}`: 最终标题 | `{year}`: 上映年份
- `{season_02}`: 补零季度 | `{episode_02}`: 补零集数
- `{team}`: 制作组 | `{resolution}`: 分辨率 | `{video_encode}`: 编码

---
*本项目由 Gemini CLI 协助进行模块化重构与功能增强。*
