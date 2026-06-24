# Phi-Plugin for AstrBot


  <p><strong>Phigros 游戏信息查询插件 - AstrBot 版本</strong></p>


## 📖 介绍

Phi-Plugin 是一个适用于 AstrBot 的 Phigros 游戏信息查询插件，从 [Yunzai-Bot V3 版本](https://github.com/Catrong/phi-plugin) 移植而来。

### ✨ 功能特性

- 🎮 **B30 成绩查询** - 查看最佳 30 首歌曲成绩
- 📊 **个人信息查询** - 查看 RKS、Challenge Mode 等信息
- 🎵 **曲目信息查询** - 查询歌曲详情、谱面信息
- 🔍 **曲目搜索** - 支持模糊搜索和别名匹配
- 📈 **推分建议** - 获取提升 RKS 的建议
- 🎯 **单曲成绩** - 查询单曲详细成绩和历史记录
- 🎲 **随机曲目** - 根据条件随机选择曲目
- 🎨 **曲绘查看** - 查看歌曲插画

### 🔄 与 Yunzai-Bot 版本的区别

| 特性 | Yunzai-Bot 版本 | AstrBot 版本 |
|------|----------------|--------------|
| 运行时 | Node.js (JavaScript) | Python 3 |
| 渲染引擎 | Puppeteer | Playwright (AstrBot 内置) |
| 配置系统 | YAML 文件 | JSON Schema |
| 消息发送 | `e.reply()` | `yield event.plain_result()` |
| 插件基类 | `plugin` | `Star` |

## 🚀 安装

### 前置要求

- AstrBot >= v4.0.0
- Python >= 3.9
- Phigros 游戏账号

### 安装步骤

1. **克隆插件到 AstrBot 插件目录**

```bash
cd AstrBot/data/plugins
git clone https://github.com/your-username/astrbot_plugin_phi-plugin.git
```

2. **安装依赖**

```bash
cd astrbot_plugin_phi-plugin
pip install -r requirements.txt
```

3. **重启 AstrBot**

在 AstrBot WebUI 中重启机器人，或使用命令：

```bash
# 如果使用 systemd
sudo systemctl restart astrbot

# 如果使用 Docker
docker restart astrbot
```

4. **验证安装**

在 AstrBot WebUI 的插件管理页面中，确认 `astrbot_plugin_phi-plugin` 已加载。

## 📝 使用说明

### 基础指令

| 指令 | 说明 | 示例 |
|------|------|------|
| `/phihelp` | 显示帮助信息 | `/phihelp` |
| `/phi bind <token>` | 绑定 sessionToken | `/phi bind abcdefghijklmnopqrstuvwxY` |
| `/phi unbind` | 解绑 sessionToken | `/phi unbind` |
| `/phi update` | 更新存档数据 | `/phi update` |

### 查询指令

| 指令 | 说明 | 示例 |
|------|------|------|
| `/phi b30` | 查询 B30 成绩 | `/phi b30` |
| `/phi info` | 查询个人信息 | `/phi info` |
| `/phi score <曲名>` | 查询单曲成绩 | `/phi score Illusionary` |
| `/phi song <曲名>` | 查询曲目信息 | `/phi song Spasmodic` |
| `/phi suggest` | 获取推分建议 | `/phi suggest` |

### 娱乐指令

| 指令 | 说明 | 示例 |
|------|------|------|
| `/phi rand` | 随机曲目 | `/phi rand 15 IN` |
| `/phi guess` | 猜曲绘 | `/phi guess` |
| `/phi jrrp` | 今日人品 | `/phi jrrp` |

### 获取 sessionToken

#### 获取方法

1. 在手机上打开 Phigros
2. 进入设置 → 存档
3. 点击「登录 TapTap」
4. 使用抓包工具（如 HttpCanary、Packet Capture 等）获取 sessionToken
5. 发送 `/phi bind <sessionToken>` 绑定

#### 获取帮助

发送 `/phi bind help` 查看详细的获取教程。

> 💡 **提示**：详细的获取方法请参考 [Phigros 非官方查分指引](https://kdocs.cn/l/cvMDjWPTNaz4)

## ⚙️ 配置说明

插件配置文件位于 `AstrBot/data/config/astrbot_plugin_phi-plugin_config.json`

### 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `renderScale` | int | 100 | 渲染精细度 (50-200) |
| `randerQuality` | int | 100 | 渲染质量 (50-100) |
| `timeout` | int | 20000 | 渲染超时时间 (ms) |
| `B19MaxNum` | int | 50 | B19 最大成绩数量 |
| `cmdhead` | string | "phi" | 命令头 |
| `openPhiPluginApi` | bool | true | 是否启用 API |
| `defaultGlobal` | bool | false | 默认使用国际服 |
| `allowComment` | bool | true | 是否开启评论功能 |
| `onLinePhiIllUrl` | int | 1 | 在线曲绘地址 (1-4) |
| `githubProxy` | string | "https://gh-proxy.com" | GitHub 代理地址 |

### 在线曲绘地址选项

| 值 | 地址 | 说明 |
|----|------|------|
| 1 | GitHub raw | 默认，需要代理 |
| 2 | Gitee raw | 国内镜像 |
| 3 | 弦塔资源站 | 第三方托管 |
| 4 | cnb.cool | 备用地址 |

## 📁 目录结构

```
astrbot_plugin_phi-plugin/
├── main.py                    # 插件主文件
├── metadata.yaml              # 插件元数据
├── _conf_schema.json          # 配置架构
├── requirements.txt           # Python 依赖
├── README.md                  # 本文件
├── LICENSE                    # 许可证
├── lib/                       # 核心库
│   ├── __init__.py
│   ├── aes.py                 # AES 加密/解密
│   ├── byte_reader.py         # 二进制数据读取器
│   ├── game_progress.py       # 游戏进度解析
│   ├── game_record.py         # 游戏记录解析
│   ├── level_record.py        # 难度记录数据类
│   ├── phigros_user.py        # 用户数据管理
│   ├── save_manager.py        # 云存档 API 客户端
│   └── util.py                # 工具函数
├── model/                     # 数据模型
│   ├── __init__.py
│   ├── chart.py               # 谱面数据类
│   ├── songs_info.py          # 曲目信息数据类
│   └── get_info.py            # 曲目元数据管理器
└── resources/                 # 资源文件
    └── info/                  # 曲目数据
        ├── info.csv           # 曲目基本信息
        ├── difficulty.csv     # 难度数据
        ├── notesInfo.json     # 物量数据
        ├── nicklist.yaml      # 曲目别名
        ├── chaplist.yaml      # 章节列表
        ├── tips.yaml          # 提示信息
        └── ...                # 其他数据文件
```

## 🔧 开发说明

### 从源码构建

```bash
# 克隆仓库
git clone https://github.com/your-username/astrbot_plugin_phi-plugin.git
cd astrbot_plugin_phi-plugin

# 安装依赖
pip install -r requirements.txt

# 代码格式化
pip install ruff
ruff format .
ruff check . --fix
```

### 添加新命令

在 `main.py` 中添加新的命令处理器：

```python
@filter.command("mycommand")
async def my_command(self, event: AstrMessageEvent, param: str = None):
    """命令描述"""
    # 命令逻辑
    yield event.plain_result("响应内容")
```

### 调试

1. 在 AstrBot WebUI 中启用插件调试模式
2. 修改代码后，点击插件管理页面的「重载插件」按钮
3. 查看 AstrBot 日志输出

## 🐛 常见问题

### Q: 绑定 sessionToken 失败

**A:** 请检查：
1. sessionToken 格式是否正确（25位字母数字组合）
2. Phigros 是否已同步存档到云端
3. 网络连接是否正常

### Q: 查询成绩显示为空

**A:** 请尝试：
1. 使用 `/phi update` 更新存档
2. 确认 sessionToken 是否过期
3. 检查是否有网络连接问题

### Q: 渲染图片失败

**A:** 请尝试：
1. 检查 AstrBot 是否正确安装了 Playwright
2. 降低 `renderScale` 配置值
3. 增加 `timeout` 超时时间

### Q: 找不到曲目

**A:** 请尝试：
1. 使用完整的曲目名称
2. 使用曲目的别名（如「鼠鼠」对应「Spasmodic」）
3. 检查 `resources/info/` 目录是否完整

## 📄 许可证

本项目基于 [ISC License](LICENSE) 许可证开源。

## 🙏 致谢

- [Yunzai-Bot](https://github.com/yoimiya-kokomi/Yunzai-Bot) - 原版机器人框架
- [phi-plugin](https://github.com/Catrong/phi-plugin) - 原版 Yunzai-Bot 插件
- [AstrBot](https://github.com/AstrBotDevs/AstrBot) - AstrBot 机器人框架
- [PhigrosLibrary](https://github.com/7aGiven/PhigrosLibrary) - 存档解析参考
- 所有贡献者和赞助者

## 🔗 链接

- [AstrBot 官方文档](https://docs.astrbot.app)
- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
- [Phi-Plugin 原版仓库](https://github.com/Catrong/phi-plugin)
- [Phigros 官方网站](https://pheez.com)

## 💬 交流

- QQ 群：975206796（AstrBot 开发者群）
- GitHub Issues：[提交问题](https://github.com/your-username/astrbot_plugin_phi-plugin/issues)
- GitHub Pull Requests：[贡献代码](https://github.com/your-username/astrbot_plugin_phi-plugin/pulls)

---

<div align="center">
  <p>如果觉得有用，请给个 ⭐ Star 支持一下！</p>
  <p>Made with ❤️ for Phigros players</p>
</div>
