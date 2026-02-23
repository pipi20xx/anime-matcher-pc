# Anime-Matcher PC (剧集视频重命名工具)

基于 [anime-matcher](https://github.com/pipi20xx/anime-matcher) 核心算法的桌面端重命名工具，采用 PyQt6 构建。本项目采用 **UI 与 逻辑完全解耦** 的模块化设计，旨在提供高效、智能、且易于维护的剧集文件整理体验。

## 🌟 特色功能

- **智能识别**：深度集成 `anime-matcher` 高级识别内核，精准提取剧集标题、季度、集数、制作组及技术规格。
- **架构解耦**：前端 UI 与后端识别引擎、重命名逻辑完全分离，支持算法核心的一键更新。
- **动态部署**：支持从 GitHub 自动下载/更新核心算法库，也支持手动拖入部署。
- **高度自定义**：
    - 支持自定义文件名、主文件夹、季文件夹的命名格式（使用 `{title}`, `{season}`, `{episode}` 等占位符）。
    - 内置强大的正则替换规则，可批量清洗文件名中的个性化噪声。
- **安全保障**：
    - **预览模式**：在执行物理重命名前，可实时预览所有文件的路径变更。
    - **自定义覆盖**：支持手动指定 TMDB ID、季度偏移或媒体类型（电影/剧集）。
- **跨平台支持**：支持 Windows、Linux 及 macOS（需安装 Python 环境）。

## 🏗️ 项目架构

项目采用层次化结构，确保代码清晰且易于扩展：

```text
/vol1/1000/NVME/anime-matcher-pc/
├── main.py                 # 程序启动入口点
├── .gitignore              # Git 忽略配置
├── VideoRenamer_Qt6.ini    # 自动生成的本地配置文件
├── src/
│   ├── gui/                # 界面层：负责 UI 渲染与异步线程调度 (QThread)
│   ├── core/               # 业务层：负责算法适配与重命名逻辑计算
│   └── utils/              # 工具层：配置管理、网络下载器、文件操作辅助
└── anime-matcher-main/     # [核心算法库]：外部导入或自动下载的识别内核
```

## 🚀 快速开始

### 1. 安装环境

确保你已安装 Python 3.10 或更高版本。

安装必要的 Python 依赖库：
```bash
pip install PyQt6 requests regex
```

### 2. 获取核心算法

本程序依赖 `anime-matcher` 核心库。你可以通过以下两种方式获取：
- **自动获取**：启动程序后，进入 **“设置”** 页签，点击 **“自动下载/更新 (GitHub)”**。
- **手动获取**：从 [GitHub 仓库](https://github.com/pipi20xx/anime-matcher) 下载 ZIP 包，解压并重命名文件夹为 `anime-matcher-main` 放置在项目根目录。

### 3. 运行程序

在项目根目录下执行：
```bash
python main.py
```

## ⚙️ 配置说明

- **文件名格式示例**：`{title} - S{season}E{episode} - {filename}`
- **主文件夹格式示例**：`({year}){title}[tmdbid={tmdbid}]`
- **季文件夹格式示例**：`Season {season_int}`

所有配置均会持久化保存于 `VideoRenamer_Qt6.ini` 中。

## 🛡️ 开关说明

- **预览模式**：仅计算路径并显示在表格中，不修改任何文件。
- **执行模式**：会根据计算出的路径执行 `os.rename` 操作，并自动创建必要的文件夹。

---
*本项目核心算法部分归原作者所有，GUI 部分由 Gemini CLI 协作构建。*
