# Anime-Matcher PC (专业级剧集整理工具)

基于 [anime-matcher](https://github.com/pipi20xx/anime-matcher) 核心算法的桌面端重命名与整理工具。本项目采用解耦的组件化架构，集成本地识别内核、云端元数据对撞及高度自定义的规则引擎。

---

## ✨ 核心特性

- **全自动识别 (L1 + L2)**：
    - **内核识别 (L1)**：精准提取文件名中的标题、集数、制作组、分辨率等原始数据。
    - **云端对撞 (L2)**：联动 **TMDB** 与 **Bangumi**，自动修正官方标题、补全上映年份。
- **解耦架构**：UI 容器与业务组件完全分离，支持算法核心的一键静默更新。
- **规则管理中心**：
    - **本地规则**：大文本框直接输入，每行一条。
    - **远程订阅**：支持从 GitHub 等地址一键同步并本地缓存规则列表。
- **用户体验优化**：
    - **智能记忆**：自动记忆窗口尺寸、分割条比例及识别过的指纹。
    - **无感拖拽**：支持文件/文件夹直接拖入，自动处理 URL 编码还原。
- **全量打包**：GitHub Actions 自动构建内置内核的完整版 EXE，真正的解压即用。

---

## 🧩 重命名支持字段 (final_result)

重命名格式支持以下 22 个全信托结论字段。使用时请用花括号包裹，如 `{title}`。

| 字段名 | 类型 | 说明 | 示例 |
| :--- | :--- | :--- | :--- |
| **title** | string | 最终采信标题 (优先使用云端/专家规则修正) | 无职转生 |
| **year** | string | 最终采信年份 | 2021 |
| **category** | string | 媒体分类 | 剧集 / 电影 |
| **season** | int | 最终决定的季度数字 | 1 |
| **season_02** | string | 季度数字补零 | 01 |
| **episode** | string | 最终决定的集数或范围 | 13 或 01-12 |
| **episode_02** | string | 集数数字补零 | 05 |
| **team** | string | 最终确定的制作小组 | Airota |
| **resolution** | string | 最终识别的分辨率 | 1080p |
| **video_encode**| string | 最终视频编码 | x265 |
| **video_effect**| string | 视频特效 | HDR / Dolby Vision |
| **audio_encode**| string | 最终音频编码 | FLAC / AAC |
| **subtitle** | string | 最终字幕语言 | CHS / CHT |
| **source** | string | 最终资源来源 | WEB-DL / BluRay |
| **platform** | string | 最终发布平台 | B-Global / Netflix |
| **origin_country**| string | 制片国家 | 日本 / 中国 |
| **release_date**| string | 正式上映/发布日期 | 2021-01-10 |
| **tmdb_id** | string | TMDB 唯一识别码 | 123456 |
| **secondary_category** | string | 二级分类全路径 | 日漫/热血 |
| **main_category** | string | 主二级分类 (仅取第一项) | 日漫 |
| **filename** | string | **清洗后**的原名 (不含后缀) | [Airota] Mushoku No.11 |
| **original_filename** | string | **原始**完整文件名 (含后缀) | [Airota] Mushoku.mkv |
| **processed_name** | string | **渲染后**原名 (由专家规则决定) | 无职转生 第11话 |
| **path** | string | 文件所在的原始完整路径 | D:\Anime\... |

---

## 🏗️ 目录结构

```text
/
├── main.py                 # 程序入口
├── README.md               # 本文档 (功能说明书)
├── .github/workflows/      # CI/CD 自动构建脚本
├── VideoRenamer_Qt6.ini    # 用户配置文件
├── VideoRenamer.db         # 本地规则数据库
├── data/                   # 核心算法生成的缓存与记忆
│   └── matcher_storage.db
├── anime-matcher-main/     # [内核] 外部导入或自动下载的算法库
└── src/
    ├── gui/                # UI 层 (MainTab, SettingsTab, RuleManager)
    ├── core/               # 业务逻辑 (Processor, Renamer, Rules)
    └── utils/              # 工具类 (Paths, Config, Downloader)
```

---

## 🚀 快速上手

### 1. 开发环境运行
```bash
pip install PyQt6 requests regex peewee zhconv cn2an httpx hishel setuptools
python main.py
```

### 2. 核心算法部署
- **自动**：启动软件 -> 设置 -> 点击“自动下载/更新 (GitHub)”。
- **手动**：将 [anime-matcher](https://github.com/pipi20xx/anime-matcher) 下载并重命名为 `anime-matcher-main` 放入根目录。

### 3. 配置联网 (L2)
- 在“设置”中填入 **TMDB API Key** (必填以激活云端对撞)。
- 如在中国大陆运行，请务必填写 **TMDB 代理地址** (如 `http://127.0.0.1:7890`)。

---

## 📦 自动发布 (GitHub Actions)

项目已配置好全自动发布流程。当你将代码从 Gitea 同步到 GitHub 时：
1. **自动构建**：Actions 会自动启动 Windows 环境。
2. **内核注入**：Actions 会自动拉取最新的 `anime-matcher` 代码。
3. **依赖补全**：Actions 会强行打包 `zhconv`, `cn2an` 等动态资源。
4. **自动发版**：Actions 会根据版本序号自动创建 Release 并上传 `AnimeProRenamer_Full_Win64.zip`。

**手动触发**：也可在 GitHub Actions 页面点击 `Run workflow` 强制重新编译完整版。

---
*本项目核心算法归原作者所有，GUI 部分由 Gemini CLI 协助构建。*
