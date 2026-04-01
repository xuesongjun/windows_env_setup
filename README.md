# Windows 开发环境配置指南

本文档覆盖 Windows 下 PowerShell 7、VS Code、代理自动检测、UTF-8 编码等配置的完整说明。

## 目录

- [快速开始](#快速开始)
- [1. 智能代理配置](#1-智能代理配置)
- [2. 启动速度优化](#2-启动速度优化)
- [3. UTF-8 编码配置](#3-utf-8-编码配置)
- [4. VS Code 配置](#4-vs-code-配置)
- [5. Git Bash 配置](#5-git-bash-配置)
- [6. Scoop 与 aria2 配置](#6-scoop-与-aria2-配置)
- [7. SSL 证书验证配置](#7-ssl-证书验证配置无管理员权限)
- [8. 故障排查](#8-故障排查)
- [9. 快速安装](#9-快速安装)

---

## 快速开始

```powershell
# 1. 运行自动配置脚本
python setup.py

# 2. 重启 PowerShell / VS Code

# 3. 运行测试验证
python test_setup.py
```

### 项目脚本说明

| 脚本 | 用途 | 运行方式 |
|------|------|---------|
| `setup.py` | 主配置脚本，一键配置 PowerShell Profile、VS Code、UTF-8、SSL、Git Bash、Scoop aria2 | `python setup.py` |
| `test_setup.py` | 验证脚本，检查所有配置是否正确生效，输出逐项测试结果 | `python test_setup.py` |
| `check_proxy.ps1` | 代理状态诊断工具，排查代理问题时使用，显示注册表/环境变量/端口/Git/npm 完整状态 | `pwsh check_proxy.ps1` |
| `enable_utf8_system.ps1` | 启用 Windows 系统级 UTF-8 支持（需管理员权限，重启后生效），解决 Claude Code 执行脚本时的中文乱码 | 管理员身份运行 `.\enable_utf8_system.ps1` |

### 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| PowerShell Profile | `~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1` | 代理自动检测和锁定逻辑 |
| VS Code 设置 | `%APPDATA%\Code\User\settings.json` | 终端、编码、Emoji 配置 |
| Git Bash 终端配置 | `~/.minttyrc` | MinTTY 字体、编码 |
| Git Bash 环境变量 | `~/.bash_profile` | UTF-8 环境变量 |
| curl 配置 | `~/.curlrc` | SSL 跳过验证 |
| 代理锁定标记 | `~/.proxy_lock` | 存在时表示代理已锁定 |

---

## 1. 智能代理配置

### 功能特性

- 启动 PowerShell 时自动检测 Windows 系统代理状态
- **动态读取 VPN 客户端端口**，无需手动配置，切换客户端后自动适配
- 代理开关变化时，新终端自动同步最新状态（包括用户级环境变量）
- **代理锁定模式**：保持代理始终开启，不跟随系统代理开关

### 代理检测原理

读取 Windows 注册表中的代理状态和地址：

```
HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings
  ProxyEnable  = 1/0       代理开关（0 关闭，1 开启）
  ProxyServer  = host:port  代理地址（如 127.0.0.1:7897）
```

`ProxyServer` 由 VPN 客户端（Clash、V2Ray 等）自动写入，切换客户端后此字段随之更新，脚本无需任何修改。

### 命令参考

> 记不住命令？在 PowerShell 中输入 `proxy` 即可查看完整列表。

| 函数名 | 别名 | 说明 |
|--------|------|------|
| `Get-ProxyHelp` | `proxy` | 显示所有代理命令帮助 |
| `Get-ProxyStatus` | `proxy-status` | 查看完整代理状态（会话/用户/Git/npm/Scoop） |
| `Lock-Proxy` | 无 | 🔒 锁定代理（不跟随系统设置，始终开启） |
| `Unlock-Proxy` | 无 | 🔓 解锁代理（恢复自动检测） |
| `Enable-Proxy` | 无 | 手动开启代理（当前会话） |
| `Disable-Proxy` | 无 | 手动关闭代理（当前会话） |
| `Sync-ProxyToTools` | `proxy-sync` | 同步代理到 git/npm/scoop |
| `Set-AutoProxy` | 无 | 重新检测系统代理状态 |
| `Update-Env` | `us` | 从注册表同步最新 Path 环境变量 |

### ⚠️ 命令命名规则

PowerShell 中**函数名必须使用首字母大写（PascalCase）**，别名使用全小写：

```powershell
Lock-Proxy      # ✅ 正确
lock-proxy      # ❌ 错误 - 找不到命令

proxy-status    # ✅ 正确（别名）
proxy-sync      # ✅ 正确（别名）
```

**原因**：PowerShell 不允许别名和函数名相同（即使大小写不同），否则会产生循环引用导致命令无法解析。

如果遇到命令找不到，重新加载 Profile：

```powershell
. $PROFILE
```

### 代理锁定模式（推荐）

**为什么需要锁定？**

| 场景 | 问题 | 解决 |
|------|------|------|
| 关闭系统代理后打开新终端 | 新终端没有代理环境变量 | 🔒 锁定代理 |
| 旧终端和新终端代理状态不一致 | 环境变量不同步 | 🔒 锁定代理 |
| 使用 Claude Code 等需要稳定代理的工具 | 代理随系统开关变化 | 🔒 锁定代理 |

```powershell
# 一次性设置，长期有效
Lock-Proxy

# 效果：
# ✅ 所有新打开的终端都自动使用代理
# ✅ Claude Code 随时可用
# ✅ 只需确保代理软件（Clash 等）在运行即可

# 解锁（恢复跟随系统代理开关）
Unlock-Proxy
```

**工作原理**：

```
自动检测模式：
系统代理开关 ON  → 设置 HTTP_PROXY → 应用使用代理
系统代理开关 OFF → 清除 HTTP_PROXY → 应用直连

锁定模式：
无论系统代理状态 → HTTP_PROXY 始终存在 → 应用始终使用代理
```

**注意**：锁定后需确保代理软件始终运行；如果代理软件未运行，应用将无法连接网络。

### 使用场景

**场景 1：日常开发（推荐）**

```powershell
# 一次性设置，长期有效
Lock-Proxy
# 此后随意开关系统代理，新终端始终保持代理状态
```

**场景 2：偶尔使用代理**

```powershell
# 检查当前状态
proxy-status

# 如果未设置，手动开启当前会话
Enable-Proxy
```

**场景 3：切换代理状态后**

切换系统代理状态后，**需要打开新终端**才能生效（新终端会重新执行 Profile 自动检测）：

1. 关闭旧终端
2. 打开新终端（Profile 重新执行，自动同步最新状态）
3. 启动应用

或直接使用锁定模式彻底避免这个问题。

### 验证代理是否正常

```powershell
# 查看完整代理状态
proxy-status

# 测试代理连接（返回 200 或 404 均表示代理正常，403 表示直连被墙）
curl -I https://api.anthropic.com

# 测试 GitHub 连接
curl -I https://github.com
```

### Profile 核心代码

```powershell
# 从注册表读取当前代理地址（适配任意 VPN 客户端端口）
function Get-SystemProxyAddress {
    $props = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -ErrorAction SilentlyContinue
    if ($props.ProxyServer) { return $props.ProxyServer }
    return $null
}

function Set-AutoProxy {
    $regPath     = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    $props       = Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue
    $proxyEnable = $props.ProxyEnable
    $proxyServer = $props.ProxyServer   # 如 "127.0.0.1:7897"

    if ($proxyEnable -eq 1 -and $proxyServer) {
        $httpProxy  = "http://$proxyServer"
        $socksProxy = "socks5://$proxyServer"   # 现代客户端（Clash 等）使用混合端口

        $env:HTTP_PROXY  = $httpProxy
        $env:HTTPS_PROXY = $httpProxy
        $env:ALL_PROXY   = $socksProxy

        # 只在值变化时写注册表，避免每次启动都写（节省约 150-300ms）
        $currentHttp = [Environment]::GetEnvironmentVariable("HTTP_PROXY", "User")
        if ($currentHttp -ne $httpProxy) {
            [Environment]::SetEnvironmentVariable("HTTP_PROXY",  $httpProxy,  "User")
            [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $httpProxy,  "User")
            [Environment]::SetEnvironmentVariable("ALL_PROXY",   $socksProxy, "User")
        }

        Write-Host "[Proxy] $httpProxy" -ForegroundColor Green
    } else {
        $env:HTTP_PROXY  = $null
        $env:HTTPS_PROXY = $null
        $env:ALL_PROXY   = $null

        $currentHttp = [Environment]::GetEnvironmentVariable("HTTP_PROXY", "User")
        if ($currentHttp) {
            [Environment]::SetEnvironmentVariable("HTTP_PROXY",  $null, "User")
            [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $null, "User")
            [Environment]::SetEnvironmentVariable("ALL_PROXY",   $null, "User")
        }

        Write-Host "[Proxy] Direct connection" -ForegroundColor Yellow
    }
}

# 启动时自动检测
Set-AutoProxy
```

---

## 2. 启动速度优化

### 问题

PowerShell 启动缓慢（>1秒），主要由于：
1. 每次启动都调用外部命令（git/npm/scoop config）
2. Conda 初始化调用 `conda.exe`（约 1.3 秒）

### 代理配置优化（已集成到 setup.py）

**原理**：启动时只设置环境变量，不调用外部命令（git/npm/scoop）。用户级环境变量只在值变化时才写注册表。

| 优化点 | 效果 |
|--------|------|
| 不调用 git/npm/scoop | 省去 3-4 秒 |
| 用户级环境变量变化检测 | 省去约 150-300ms |
| 动态读取代理端口 | 切换 VPN 客户端无需重跑脚本 |

### Conda 延迟加载优化（手动配置）

如果使用 Conda，将初始化推迟到首次调用时：

```powershell
#region Conda 延迟加载
function Initialize-Conda {
    & "C:\Users\<用户名>\miniconda3\Scripts\conda-hook.ps1"
    conda activate base
}

function conda {
    Initialize-Conda
    & "C:\Users\<用户名>\miniconda3\Scripts\conda.exe" $args
}

Set-Alias -Name init-conda -Value Initialize-Conda
#endregion
```

**效果**：
- 启动时不加载 conda（节省 1.3 秒）
- 首次使用 `conda` 命令时自动初始化
- 也可手动初始化：`init-conda`

### 性能对比

| 项目 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 代理配置 | ~100ms + 外部命令 | ~50ms | 快速 |
| Conda 初始化 | 1356ms | 12ms（延迟加载） | 113x |
| **总启动时间** | **~1400ms** | **~450ms** | **3x** |

### 脚本中的 UTF-8 编码

如果在脚本中使用 `pwsh -NoProfile`，需要在脚本开头添加 UTF-8 编码设置：

```powershell
# UTF-8 编码设置（确保中文正常显示）
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 >$null 2>&1
```

**原因**：`-NoProfile` 会跳过 Profile 中的 UTF-8 配置，导致中文乱码。

---

## 3. UTF-8 编码配置

### 问题

Windows 默认使用 GBK（代码页 936），导致中文乱码。

### 解决方案

在 PowerShell Profile 中添加（`setup.py` 自动配置）：

```powershell
# ========== UTF-8 编码设置 ==========
[Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"                   # Python 3.7+ 默认 UTF-8 模式
$env:PYTHONIOENCODING = "utf-8"         # Python I/O 编码
$env:LANG = "en_US.UTF-8"
$env:LC_ALL = "en_US.UTF-8"
chcp 65001 >$null 2>&1
```

### 用户级环境变量（永久生效）

`setup.py` 会自动将以下环境变量持久化到用户级（通过注册表写入）：

| 环境变量 | 作用 | 生效范围 |
|---------|------|---------|
| `PYTHONUTF8=1` | Python 3.7+ UTF-8 模式，影响文件读写、`open()` 默认编码 | 用户级永久（所有终端） |
| `PYTHONIOENCODING=utf-8` | 标准输入/输出/错误流的编码 | 用户级永久（所有终端） |
| `LANG=en_US.UTF-8` | 系统区域设置 | 用户级永久（所有终端） |

覆盖场景：PowerShell、CMD、Git Bash、`pwsh -NoProfile`、IDE 子进程等。解决了 `pip install` 在 GBK 环境下报 `UnicodeDecodeError` 的问题。

### 系统级 UTF-8（需管理员权限，需重启）

```powershell
# 以管理员身份运行
.\enable_utf8_system.ps1
```

或手动设置：控制面板 > 区域 > 管理 > 更改系统区域设置 > 勾选"Beta: 使用 Unicode UTF-8 提供全球语言支持"

### Python 脚本编码

在 Python 脚本开头添加：

```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
```

---

## 4. VS Code 配置

### 配置 PowerShell 7 为默认终端（含 Emoji 支持）

**位置**: `%APPDATA%\Code\User\settings.json`

```json
{
    "terminal.integrated.defaultProfile.windows": "PowerShell 7",
    "terminal.integrated.profiles.windows": {
        "PowerShell 7": {
            "path": "C:\\Users\\<用户名>\\AppData\\Local\\Programs\\PowerShell\\7.5.4\\pwsh.exe",
            "icon": "terminal-powershell",
            "args": ["-NoExit", "-NoLogo", "-Command", "chcp 65001 > $null"],
            "env": {
                "LANG": "en_US.UTF-8",
                "LC_ALL": "en_US.UTF-8",
                "PYTHONIOENCODING": "utf-8"
            }
        }
    },
    "terminal.integrated.env.windows": {
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "PYTHONIOENCODING": "utf-8"
    },
    "terminal.integrated.fontFamily": "Cascadia Mono, Consolas, 'Courier New', monospace",
    "terminal.integrated.unicodeVersion": "11",
    "terminal.integrated.gpuAcceleration": "off",
    "files.encoding": "utf8",
    "files.autoGuessEncoding": true,
    "terminal.external.windowsExec": "wt.exe"
}
```

### Emoji 支持关键配置

| 配置项 | 值 | 作用 |
|-------|-----|------|
| `terminal.integrated.fontFamily` | `Cascadia Mono, ...` | 使用支持 Emoji 的字体 |
| `terminal.integrated.unicodeVersion` | `11` | 使用 Unicode 11 宽度计算 |
| `args` | `["-NoExit", "-Command", "chcp 65001"]` | 终端启动时设置 UTF-8 代码页 |
| `terminal.integrated.gpuAcceleration` | `off` | 解决部分 Emoji 渲染问题 |

### 常用命令

```powershell
# 查找 PowerShell 7 路径
Get-Command pwsh | Select-Object Source

# 查看当前代理环境变量
Get-ChildItem Env: | Where-Object { $_.Name -like "*proxy*" }
```

---

## 5. Git Bash 配置

### .minttyrc（MinTTY 终端配置）

**位置**: `~/.minttyrc`

```ini
# Git Bash (MinTTY) Configuration for UTF-8 and emoji support
Charset=UTF-8
Locale=en_US
Font=Cascadia Mono
FontHeight=11
Term=xterm-256color
CursorType=block
Scrollbar=none
BoldAsFont=no
AllowBlinking=yes
```

### .bash_profile（Bash 环境变量）

**位置**: `~/.bash_profile`

```bash
# UTF-8 Configuration for Git Bash
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export TERM=xterm-256color
```

### 关键配置说明

| 配置项 | 作用 |
|-------|------|
| `Charset=UTF-8` | MinTTY 使用 UTF-8 字符集 |
| `Font=Cascadia Mono` | 使用支持 Emoji 的字体 |
| `LANG=en_US.UTF-8` | Bash 环境 UTF-8 |

---

## 6. Scoop 与 aria2 配置

### 什么是 aria2？

**aria2** 是一个轻量级多协议命令行下载工具，支持多连接并行下载、断点续传，以及配置跳过 SSL 证书验证。

### 为什么 Scoop 需要 aria2？

Scoop 默认使用 .NET 的 `Invoke-WebRequest` 下载文件。当使用 Clash 等代理软件（启用 HTTPS 解密/MITM）时，会遇到 SSL 证书验证错误：

```
The SSL connection could not be established
未能为 SSL/TLS 安全通道建立信任关系
```

| 对比项 | .NET Invoke-WebRequest | aria2 |
|--------|------------------------|-------|
| SSL 证书验证 | 严格验证，无法跳过 | 可配置 `--check-certificate=false` |
| 多线程下载 | 单线程 | 多连接并行下载，速度更快 |
| 代理兼容性 | 对 MITM 代理不友好 | 良好 |

### HTTPS 解密（MITM）影响的程序

**受影响**（会报 SSL 证书错误）：

| 程序/库 | 解决方法 |
|---------|---------|
| .NET (Scoop, Invoke-WebRequest) | 使用 aria2 |
| Node.js | `NODE_TLS_REJECT_UNAUTHORIZED=0` |
| Python requests/pip | `verify=False` / `--trusted-host` |

**不受影响**（可跳过验证）：curl（`-k`）、aria2（`--check-certificate=false`）、Git（`http.sslVerify false`）

### 根本解决方案：安装 Clash CA 证书

如果 Clash 启用了 HTTPS 解密（MITM），可将其 CA 证书导入 Windows：

```powershell
# 导出 CA 证书：Clash 设置 > TLS > 导出 CA 证书

# 以管理员权限导入
Import-Certificate -FilePath "path\to\clash-ca.crt" -CertStoreLocation Cert:\LocalMachine\Root
```

或双击 `.crt` 文件 > 安装证书 > 本地计算机 > 受信任的根证书颁发机构。

安装后可以移除跳过验证的配置。

### 安装和配置

#### 步骤 1：安装 aria2

如果 Scoop 已经出现 SSL 错误，需要手动下载：

```powershell
# 使用 curl 手动下载（-k 跳过证书验证）
curl -k -x $env:HTTP_PROXY -L -o "$env:USERPROFILE/scoop/cache/aria2-temp.zip" "https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip"

# 重命名为 scoop 缓存格式
Move-Item "$env:USERPROFILE/scoop/cache/aria2-temp.zip" "$env:USERPROFILE/scoop/cache/aria2#1.37.0-1#https_github.com_aria2_aria2_releases_download_release-1.37.0_aria2-1.37.0-win-64bit-build1.zip"

# 从缓存安装
scoop install aria2
```

#### 步骤 2：配置 Scoop 使用 aria2

```powershell
scoop config aria2-enabled true
scoop config aria2-options '--check-certificate=false'
scoop config aria2-warning-enabled false
```

---

## 7. SSL 证书验证配置（无管理员权限）

### 问题背景

当系统缺少 USERTrust ECC 根证书，且没有管理员权限安装时，许多 HTTPS 连接会失败。

**安全警告**：跳过 SSL 验证会降低安全性，仅在受信任的网络环境中使用。

### 自动配置（推荐）

运行 `setup.py` 会自动配置所有工具：

```powershell
python setup.py
```

### 手动配置

```powershell
# curl（创建 ~/.curlrc）
echo insecure > ~/.curlrc

# Git
git config --global http.sslVerify false

# npm
npm config set strict-ssl false
```

在 PowerShell Profile 中添加（`setup.py` 已自动配置）：

```powershell
$env:NODE_TLS_REJECT_UNAUTHORIZED = "0"  # Node.js
$env:PYTHONHTTPSVERIFY = "0"             # Python
```

### 配置汇总

| 工具 | 配置方法 | 配置文件/命令 |
|------|---------|--------------|
| curl | ~/.curlrc | `insecure` |
| Git | git config | `http.sslVerify false` |
| npm | npm config | `strict-ssl false` |
| Node.js | 环境变量 | `NODE_TLS_REJECT_UNAUTHORIZED=0` |
| Python | 环境变量 | `PYTHONHTTPSVERIFY=0` |
| Scoop | aria2 | `--check-certificate=false` |

### 有管理员权限时的根本解决方案

```powershell
# 以管理员权限运行
Import-Certificate -FilePath "USERTrust_ECC_Root.crt" -CertStoreLocation Cert:\LocalMachine\Root
```

---

## 8. 故障排查

### 代理相关

**症状：新终端没有代理，旧终端有代理**

原因：新终端打开时系统代理已关闭，Profile 执行时未设置环境变量。

```powershell
# 方案 1：锁定代理（推荐，一劳永逸）
Lock-Proxy

# 方案 2：手动开启当前会话
Enable-Proxy

# 方案 3：检查状态
proxy-status
```

---

**症状：提示 `Lock-Proxy` 找不到命令**

```powershell
# 1. 确认首字母大写：Lock-Proxy（不是 lock-proxy）

# 2. 重新加载 Profile
. $PROFILE

# 3. 确认函数已加载
Get-Command Lock-Proxy -CommandType Function

# 4. 如有旧版别名冲突，清除后重载
Remove-Alias lock-proxy -ErrorAction SilentlyContinue
Remove-Alias unlock-proxy -ErrorAction SilentlyContinue
. $PROFILE

# 5. 仍然无效则重新运行配置
python setup.py
```

---

**症状：代理已锁定但仍无法连接**

```powershell
# 检查代理软件是否运行
proxy-status

# 测试代理连接（200/404 正常，403 表示直连被墙）
curl -I https://api.anthropic.com
```

---

**症状：不同终端代理状态不一致**

用户级环境变量对所有新程序生效，但需要重启程序才能读取新值。

```powershell
# 关闭所有旧终端，打开新终端
# 或使用锁定模式彻底避免此问题
Lock-Proxy
```

---

### 中文乱码

**症状：PowerShell 或 Claude Code 输出中文乱码**

```powershell
# 以管理员身份运行（只需一次，重启后永久生效）
.\enable_utf8_system.ps1
```

或手动设置：控制面板 > 区域 > 管理 > 更改系统区域设置 > 勾选"Beta: 使用 Unicode UTF-8 提供全球语言支持"，重启计算机。

---

### VS Code 终端 Emoji 乱码

**原因**: VS Code 终端基于 xterm.js，在 Windows 上的 Unicode 处理有问题。

**解决**：运行 `python setup.py` 会自动配置 Cascadia Mono 字体、Unicode 版本 11、GPU 加速关闭。

如果仍有问题，使用 Windows Terminal（`Ctrl+Shift+C` 打开外部终端）。

相关 Issue: [xtermjs/xterm.js#2693](https://github.com/xtermjs/xterm.js/issues/2693)、[microsoft/vscode#206468](https://github.com/microsoft/vscode/issues/206468)

---

## 9. 快速安装

### 前置条件

1. 安装 PowerShell 7: https://github.com/PowerShell/PowerShell/releases
2. 安装 Scoop: https://scoop.sh/
3. 安装 Python 3.7+

### 自动配置脚本

```powershell
python setup.py
```

该脚本会自动配置：
- 用户级 UTF-8 环境变量（PYTHONUTF8、PYTHONIOENCODING、LANG）
- PowerShell Profile（代理自动检测/锁定、UTF-8 编码、SSL 环境变量）
- VS Code 设置（PowerShell 7 终端、Emoji 支持）
- Git Bash 配置（.minttyrc、.bash_profile UTF-8）
- SSL 证书验证跳过（curl/Git/npm，无管理员权限方案）
- Scoop aria2 下载器

**注意**：重复运行 `setup.py` 会自动更新已有配置，不会跳过。

### 测试脚本

```powershell
python test_setup.py
```

验证所有配置是否正确。

### 手动安装常用工具

```powershell
# 文档处理工具
scoop install pandoc poppler qpdf tesseract

# OCR 中文语言包
curl -k -x $env:HTTP_PROXY -L -o "$env:USERPROFILE\scoop\apps\tesseract\current\tessdata\chi_sim.traineddata" "https://github.com/tesseract-ocr/tessdata_fast/raw/main/chi_sim.traineddata"
```

---

## 参考链接

- [PowerShell 7 下载](https://github.com/PowerShell/PowerShell/releases)
- [VS Code 设置](https://code.visualstudio.com/docs/getstarted/settings)
- [Scoop 包管理器](https://scoop.sh/)
- [aria2 项目](https://github.com/aria2/aria2)
