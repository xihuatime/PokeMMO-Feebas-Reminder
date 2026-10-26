# 鱼点刷新提醒工具 🐟

一个常驻 Windows 系统托盘的周期提醒小工具：**以每日 22:15 为时间锚点、45 分钟为固定周期全天循环提醒**，到点弹系统通知 + 置顶小窗 + 可选提示音，内容固定为「鱼点已刷新」。

单文件 exe，双击即用，不占资源，适合长期挂在后台。

[**⬇️ 下载最新版本**](../../releases/latest) · [查看全部版本](../../releases)

---

## 功能特性

- **精确周期**：锚点 22:15 + 45 分钟周期，全天 24 小时循环，跨天不重置
- **三种提醒**：系统通知（Windows 通知中心）+ 置顶弹窗 + 提示音（可单独关闭）
- **托盘常驻**：启动即隐藏主窗口，右键托盘图标可开关提醒、测试、退出
- **状态可见**：鼠标悬停托盘图标显示「下次提醒 HH:MM」
- **低占用**：单进程，常驻内存约 30–50 MB，空闲时 CPU 接近 0
- **零依赖运行**：exe 已内置 Python 运行时，目标机器无需安装任何环境

## 提醒时刻规则

| 项目 | 值 |
| --- | --- |
| 时间锚点 | 每日 22:15（仅用于标定周期相位） |
| 提醒周期 | 45 分钟 |
| 覆盖范围 | 全天 24 小时循环 |
| 提醒内容 | 鱼点已刷新 |

所有提醒时刻与当日 22:15 的时间差都是 45 分钟的整数倍，向前向后都循环计算：

```
22:15 → 23:00 → 23:45 → 00:30 → 01:15 → 02:00 → … → 21:30 → 22:15（次日）
```

**为什么不需要"每天重置"**：24 小时 = 1440 分钟，1440 ÷ 45 = 32 整除，所以 45 分钟周期在一天里正好走满 32 格，锚点相位每天都一样。代码里直接对锚点做绝对分钟数取整即可，跨天、跨月、跨年自动延续。

## 下载使用

1. 打开 [Releases](../../releases/latest) 页面
2. 下载最新版本里的 `鱼点刷新提醒工具.exe`
3. 双击运行，托盘出现绿色小鱼图标即启动成功

> 首次运行 Windows SmartScreen 可能提示「已保护你的电脑」，点「更多信息」→「仍要运行」即可（exe 未做代码签名，属于正常现象）。

### 托盘菜单

| 菜单项 | 说明 |
| --- | --- |
| 开启提醒 | 勾选 = 运行，取消 = 暂停（程序仍在后台，随时可恢复） |
| 提示音 | 控制到点是否播放系统提示音 |
| 立即提醒一次 | 立刻走一遍完整提醒流程，用于验证效果（双击托盘图标同效） |
| 退出 | 彻底结束进程 |

### 开机自启（可选）

`Win + R` 输入 `shell:startup` 打开启动目录，把 `鱼点刷新提醒工具.exe` 的**快捷方式**放进去即可。

## 本地运行（源码方式）

```bash
git clone <你的仓库地址>
cd <仓库目录>
pip install -r requirements.txt
python reminder.py
```

无控制台窗口运行：

```bash
pythonw reminder.py
```

只验证时刻算法、不启动界面（跑内置断言自检）：

```bash
python reminder.py --selfcheck
```

## 打包 exe

### 方式一：一键脚本（推荐本地测试用）

双击 `build_exe.bat`，脚本会自动检查环境 → 安装依赖 → 打包，产物输出到 `dist\鱼点刷新提醒工具.exe`。

### 方式二：手动命令行

```bash
pip install -r requirements.txt pyinstaller
python -m PyInstaller --onefile --windowed --name "鱼点刷新提醒工具" reminder.py
```

固定参数说明：

| 参数 | 作用 |
| --- | --- |
| `--onefile` | 打成单个 exe 文件 |
| `--windowed` | 不显示控制台黑框（GUI 程序必加） |
| `--name` | 指定产物名称 |

> 用 `python -m PyInstaller` 而不是裸 `pyinstaller`，可以避免 Python 的 Scripts 目录不在 PATH 时提示「命令不存在」。

### ⚠️ 打包前必看

本地打包需要 **Python 安装时勾选了 `tcl/tk and IDLE` 组件**，否则会报 `No module named 'tkinter'`，或者打出来的 exe 弹窗功能失效。

修复方法：重新运行 Python 安装包 → `Modify` → 勾选 `tcl/tk and IDLE` → `Install`。`build_exe.bat` 已内置这项检查，缺失时会直接提示。

## 自动发布（GitHub Actions）

仓库内置工作流 `.github/workflows/build-release.yml`：**推送 `v*` 格式的标签时自动打包并创建 Release**。

### 完整发布流程

```bash
# 1. 首次把项目推上 GitHub（在本目录下执行）
git init
git add .
git commit -m "feat: 鱼点刷新提醒工具首个版本"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main

# 2. 打标签（版本号按需修改）
git tag -a v1.0.0 -m "v1.0.0 首个版本"

# 3. 推送标签 —— 这一步才会触发自动构建
git push origin v1.0.0
```

4. 打开仓库的 **Actions** 页面，可以看到 `Build and Release` 工作流正在运行（约 2–4 分钟）
5. 构建完成后，进入 **Releases** 页面，会看到自动创建的 `鱼点刷新提醒工具 v1.0.0`，附件即为 exe
6. Release 说明中的「更新内容」区块支持发布后手动编辑补充（工作流也会自动追加本次提交记录）

### 后续发版

```bash
git add .
git commit -m "fix: 修复 xxx"
git push
git tag -a v1.1.0 -m "v1.1.0"
git push origin v1.1.0
```

### 工作流说明

| 环节 | 内容 |
| --- | --- |
| 触发条件 | 仅 `push` 形如 `v*` 的标签，普通提交不会触发 |
| 运行环境 | `windows-latest` |
| Python | 3.11（官方镜像自带 tcl/tk，tkinter 可用） |
| 打包命令 | `--onefile --windowed --name "鱼点刷新提醒工具"`（工作流里用 `shell: python` 直接调 PyInstaller 接口，参数完全一致） |
| 发布 | 用 `GITHUB_TOKEN` 创建同名 Release 并上传 `dist/*.exe` |

> 若需要修改 exe 文件名或发布说明模板，改 `build-release.yml` 中「打包 exe」和「创建 Release 并上传附件」两步即可。
>
> **为什么打包步骤用 `shell: python` 而不是直接写命令行**：GitHub 的 Windows runner 上，中文参数经过 shell 传参时会被系统代码页改写，实测产物名会变成 `default.exe`。改成在 Python 里直接调 `PyInstaller.__main__.run([...])`，参数以字符串形式传入，不经过 shell，产物名就稳定了。工作流还额外加了一步「规范产物名」兜底，无论 PyInstaller 起什么名，最终都会统一成 `鱼点刷新提醒工具.exe`。

## 项目结构

```
.
├── .github/
│   └── workflows/
│       └── build-release.yml   # 推 v* 标签自动打包并发布 Release
├── reminder.py                 # 主程序：周期算法 + 托盘 + 通知 + 弹窗
├── requirements.txt            # 运行依赖（pystray、Pillow）
├── build_exe.bat               # 本地一键打包脚本
├── start_silent.bat            # 源码方式静默启动（无控制台）
├── .gitignore
└── README.md
```

## 自定义参数

`reminder.py` 顶部常量，改完重新打包即可：

```python
ANCHOR = datetime(2020, 1, 1, 22, 15)  # 锚点日期随意，程序只取 22:15 这个相位
PERIOD_MIN = 45                        # 提醒周期（分钟）
MESSAGE = "鱼点已刷新"                  # 提醒文字
POPUP_SECONDS = 8                      # 弹窗停留秒数
```

> ⚠️ `PERIOD_MIN` 需要能整除 1440（如 30 / 45 / 60 / 90 / 120），才能保证每天都是同一批时刻。改成 50 这类不能整除的值，锚点会逐日漂移——程序仍能运行，但不再对应「每日 22:15」。

## 常见问题

**Q：打包或运行时报 `No module named 'tkinter'`**
A：Python 安装时没勾 `tcl/tk and IDLE`。重新运行安装包 → `Modify` → 勾选该组件 → 安装完成后重新打包。

**Q：改了周期后，提醒时间每天都在变（周期漂移）**
A：因为 `PERIOD_MIN` 不能整除 1440。请选择 30 / 45 / 60 / 90 / 120 这类能整除 24 小时的周期值。

**Q：有弹窗和声音，但没有系统通知**
A：Windows 专注助手 / 勿扰模式会拦截通知。到「设置 → 系统 → 通知」里允许该程序通知即可，弹窗和提示音不受影响。

**Q：电脑睡眠期间错过了提醒怎么办**
A：唤醒后会立刻补发一次（不补发历史错过的多个时间点），随后回到正常节奏。

**Q：双击 exe 没反应 / 托盘没有图标**
A：先确认任务管理器里是否有该进程；若有进程无图标，多半是托盘图标被收进了 Windows 的「隐藏的图标」区域，点托盘箭头展开即可。杀毒软件误杀也会导致启动失败，可加入白名单后重试。

**Q：能不能改成开机自启**
A：可以，见上文「开机自启」章节；程序本身不做注册表写入，避免影响系统。

## 许可

本项目仅供个人学习与自用。如需转载或商用，请先联系作者。
