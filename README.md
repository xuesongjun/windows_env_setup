# Windows 开发环境配置指南

本文档汇总了 Windows 下 PowerShell 7、VS Code、代理自动检测、UTF-8 编码等配置方法。

## 目录

- [1. 智能代理配置](#1-智能代理配置)
- [2. 启动速度优化](#2-启动速度优化)
- [3. UTF-8 编码配置](#3-utf-8-编码配置)
- [4. VS Code 配置](#4-vs-code-配置)
- [5. Git Bash 配置](#5-git-bash-配置)
- [6. Scoop 与 aria2 配置](#6-scoop-与-aria2-配置)
- [7. SSL 证书验证配置（无管理员权限）](#7-ssl-证书验证配置无管理员权限)
- [8. 已知问题](#8-已知问题)
- [9. 快速安装](#9-快速安装)

---

## 1. 智能代理配置

### 功能

- 启动 PowerShell 时自动检测 Windows 代理设置开关
- 代理开启时自动配置：环境变量、Git、Scoop、npm
- 代理关闭时自动清除所有代理配置
- **代理锁定模式**：保持代理始终开启，不跟随系统代理开关（推荐用于 Claude Code）

### 配置文件

**位置**: `$HOME\Documents\PowerShell\Microsoft.PowerShell_profile.ps1`

```powershell
# ========== 智能代理配置 ==========
# 兜底默认值（注册表读取失败时使用）
$PROXY_FALLBACK_HOST_PORT = "127.0.0.1:7890"

# 从注册表读取当前代理地址（适配任意 VPN 客户端端口）
function Get-SystemProxyAddress {
    $props = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -ErrorAction SilentlyContinue
    if ($props.ProxyServer) { return $props.ProxyServer }
    return $null
}

function Set-AutoProxy {
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
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

### 可用命令

输入 `proxy` 即可查看所有代理相关命令的快速帮助。

| 命令 | 别名 | 功能 |
|------|------|------|
| `Get-ProxyHelp` | `proxy` | 显示所有代理命令帮助 |
| `Get-ProxyStatus` | `proxy-status` | 查看完整代理状态（会话/用户/Git/npm/Scoop） |
| `Lock-Proxy` | — | 🔒 锁定代理（不跟随系统设置，始终开启） |
| `Unlock-Proxy` | — | 🔓 解锁代理（恢复自动检测） |
| `Enable-Proxy` | — | 手动开启代理（当前会话） |
| `Disable-Proxy` | — | 手动关闭代理（当前会话） |
| `Sync-ProxyToTools` | `proxy-sync` | 同步代理到 git/npm/scoop |
| `Set-AutoProxy` | — | 重新检测系统代理状态 |

**提示**：记不住命令？输入 `proxy` 即可查看完整列表。

### 代理检测原理

读取 Windows 注册表中的代理状态和地址：

```
HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings
  ProxyEnable  = 1/0      代理开关
  ProxyServer  = host:port 代理地址（如 127.0.0.1:7897）
```

`ProxyServer` 由 VPN 客户端（Clash、V2Ray 等）写入，切换客户端后自动适配，无需修改脚本。

### 🔒 代理锁定模式（推荐用于 Claude Code）

**为什么需要代理锁定？**

在使用 Claude Code 等需要稳定代理连接的应用时，可能会遇到以下问题：

| 场景 | 问题 | 原因 |
|------|------|------|
| 关闭系统代理后打开新终端 | Claude Code 无法连接 | 新终端没有代理环境变量 |
| 代理开启时的旧终端 | 关闭代理后仍能正常使用 | 旧终端保留了代理环境变量 |
| API 中转站访问 | 直连慢且不稳定 | 通过代理访问更快更稳定 |

**解决方案：锁定代理模式**

代理锁定后，无论 Windows 系统代理开关状态如何，代理环境变量始终存在。

**使用方法**：

```powershell
# 锁定代理（推荐）
Lock-Proxy

# 效果：
# - 所有新打开的终端都会自动设置代理环境变量
# - Claude Code 等应用随时可用
# - 只要代理软件（Clash）在运行即可，无需开启系统代理开关

# 查看状态
Get-ProxyStatus  # 或 proxy-status

# 解锁（恢复自动检测）
Unlock-Proxy
```

**工作原理**：

```
锁定前（自动检测模式）：
Windows 系统代理开关 ON  → 设置 HTTP_PROXY 环境变量 → 应用使用代理
Windows 系统代理开关 OFF → 清除 HTTP_PROXY 环境变量 → 应用直连

锁定后（锁定模式）：
无论系统代理开关状态 → HTTP_PROXY 始终设置 → 应用始终使用代理
```

**适用场景**：

- ✅ 使用 Claude Code 等需要稳定代理的应用
- ✅ API 中转站通过代理访问更快更稳定
- ✅ 希望代理配置独立于系统代理开关
- ✅ 代理软件始终在后台运行（如 Clash 常驻）

**注意事项**：

- ⚠️ 锁定后需要确保代理软件（Clash/V2Ray）始终运行
- ⚠️ 如果代理软件未运行，应用将无法连接网络
- ⚠️ 浏览器等系统级应用仍跟随系统代理开关（不受锁定影响）

---

## 2. 启动速度优化

### 问题

PowerShell 启动缓慢（>1秒），主要由于：
1. 每次启动都调用外部命令（git/npm/scoop config）
2. Conda 初始化调用 `conda.exe`（约 1.3 秒）

### 优化方案

#### 代理配置优化（已集成到 setup.py）

**原理**：启动时只设置环境变量，不调用外部命令（git/npm/scoop）。用户级环境变量只在值变化时才写注册表，避免每次启动都写。

| 优化点 | 效果 |
|--------|------|
| 不调用 git/npm/scoop | 省去 3-4 秒 |
| 用户级环境变量变化检测 | 省去约 150-300ms |
| 动态读取代理端口 | 切换 VPN 客户端无需重跑脚本 |

**新增命令**：

| 命令 | 别名 | 功能 |
|------|------|------|
| `Get-ProxyHelp` | `proxy` | 显示所有代理命令帮助 |
| `Sync-ProxyToTools` | `proxy-sync` | 手动同步代理到 git/npm/scoop |
| `Get-ProxyStatus` | `proxy-status` | 查看所有工具的代理配置状态 |

**使用说明**：
- Git、Python、curl 等自动读取环境变量，无需额外操作
- npm 首次使用前运行 `proxy-sync` 同步配置
- 切换代理状态后，如需更新 npm 配置，运行 `proxy-sync`

#### Conda 延迟加载

**问题**：每次启动都运行 `conda.exe "shell.powershell" "hook"`，耗时约 1.3 秒。

**解决方案**：只在首次使用 conda 命令时才初始化。

在 `~/Documents/PowerShell/profile.ps1` 中添加：

```powershell
#region conda initialize (lazy loading)
$global:CondaInitialized = $false

function Initialize-Conda {
    if (-not $global:CondaInitialized) {
        Write-Host "Initializing conda..." -ForegroundColor Cyan
        If (Test-Path "C:\Users\<用户名>\miniconda3\Scripts\conda.exe") {
            (& "C:\Users\<用户名>\miniconda3\Scripts\conda.exe" "shell.powershell" "hook") | Out-String | ?{$_} | Invoke-Expression
        }
        $global:CondaInitialized = $true
        Write-Host "Conda initialized." -ForegroundColor Green
    }
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

Windows 默认使用 GBK (代码页 936)，导致中文乱码。

### 解决方案

在 PowerShell profile 中添加：

```powershell
# ========== UTF-8 编码设置 ==========
[Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"                   # Python 3.7+ 默认 UTF-8 模式
$env:PYTHONIOENCODING = "utf-8"         # Python I/O 编码
$env:LANG = "en_US.UTF-8"
$env:LC_ALL = "en_US.UTF-8"
chcp 65001 >$null 2>&1

# 设置用户级环境变量（永久生效，对所有新进程有效）
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
[Environment]::SetEnvironmentVariable("PYTHONIOENCODING", "utf-8", "User")
```

### Python UTF-8 模式说明

`setup.py` 会自动将以下环境变量持久化到用户级（通过注册表写入），确保所有场景都生效：

| 环境变量 | 作用 | 生效范围 |
|---------|------|---------|
| `PYTHONUTF8=1` | Python 3.7+ UTF-8 模式，影响文件读写、`open()` 默认编码 | 用户级永久（所有终端） |
| `PYTHONIOENCODING=utf-8` | 标准输入/输出/错误流的编码 | 用户级永久（所有终端） |
| `LANG=en_US.UTF-8` | 系统区域设置 | 用户级永久（所有终端） |

**覆盖场景**：PowerShell、CMD、Git Bash、`pwsh -NoProfile`、IDE 子进程等。
解决了 `pip install -r requirements.txt` 在 GBK 环境下报 `UnicodeDecodeError` 的问题。

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

### 查找 PowerShell 7 路径

```powershell
Get-Command pwsh | Select-Object Source
```

### 查询Proxy代理地址
```powershell
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

**aria2** 是一个轻量级的多协议命令行下载工具，支持：
- HTTP/HTTPS 下载
- FTP 下载
- BitTorrent 下载
- 多连接并行下载（加速）
- 断点续传
- 可配置跳过 SSL 证书验证

### 为什么 Scoop 需要 aria2？

Scoop 默认使用 .NET 的 `Invoke-WebRequest` 下载文件。当使用 Clash 等代理软件（启用 HTTPS 解密/MITM）时，会遇到 SSL 证书验证错误：

```
The SSL connection could not be established
未能为 SSL/TLS 安全通道建立信任关系
```

**原因分析**：

| 对比项 | .NET Invoke-WebRequest | aria2 |
|--------|------------------------|-------|
| SSL 证书验证 | 严格验证，无法跳过 | 可配置 `--check-certificate=false` |
| 多线程下载 | 单线程 | 多连接并行下载，速度更快 |
| 断点续传 | 有限支持 | 完整支持 |
| 代理兼容性 | 对 MITM 代理不友好 | 良好 |

Clash 等代理软件启用 HTTPS 解密时，会用自己的证书替换原始证书。.NET 不信任这个证书就会报错，而 aria2 可以配置跳过证书验证。

### HTTPS 解密（MITM）影响的程序

**受影响的程序**（会报 SSL 证书错误）：

| 程序/库 | 原因 | 临时解决方法 |
|---------|------|-------------|
| .NET (Scoop, Invoke-WebRequest) | 严格验证系统证书 | 使用 aria2 |
| Node.js | 默认严格验证 | `NODE_TLS_REJECT_UNAUTHORIZED=0` |
| Python requests/pip | 默认严格验证 | `verify=False` / `--trusted-host` |
| Java | 使用独立证书存储 | 导入证书到 JKS |

**不受影响的程序**（可配置跳过验证）：

| 程序 | 跳过验证方法 |
|------|-------------|
| curl | `-k` 或 `--insecure` |
| aria2 | `--check-certificate=false` |
| Git | `git config http.sslVerify false` |
| 浏览器 | 通常自动导入系统证书 |

### 根本解决方案：安装 Clash CA 证书

如果你的 Clash 启用了 HTTPS 解密（MITM），可以将其 CA 证书导入 Windows，这样所有程序都会信任它：

1. **导出 Clash CA 证书**
   - 打开 Clash 设置 > TLS > 导出 CA 证书
   - 或在 Clash 配置目录找到 `ca.crt` 文件

2. **导入到 Windows 受信任的根证书存储**
   ```powershell
   # 以管理员权限运行
   Import-Certificate -FilePath "path\to\clash-ca.crt" -CertStoreLocation Cert:\LocalMachine\Root
   ```

   或者双击 `.crt` 文件 > 安装证书 > 本地计算机 > 受信任的根证书颁发机构

3. **验证**
   ```powershell
   # 不使用 -k 也能正常访问
   curl -x $env:HTTP_PROXY https://github.com
   ```

**注意**：安装 CA 证书意味着信任该证书签发的所有证书，请确保只在受信任的环境中使用。

### 安装和配置

#### 步骤 1：安装 aria2

如果 scoop 已经出现 SSL 错误，需要手动下载 aria2：

```powershell
# 使用 curl 手动下载（-k 跳过证书验证）
curl -k -x $env:HTTP_PROXY -L -o "$env:USERPROFILE/scoop/cache/aria2-temp.zip" "https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip"

# 重命名为 scoop 缓存格式
Move-Item "$env:USERPROFILE/scoop/cache/aria2-temp.zip" "$env:USERPROFILE/scoop/cache/aria2#1.37.0-1#https_github.com_aria2_aria2_releases_download_release-1.37.0_aria2-1.37.0-win-64bit-build1.zip"

# 从缓存安装
scoop install aria2
```

#### 步骤 2：配置 scoop 使用 aria2

```powershell
# 启用 aria2 作为下载器
scoop config aria2-enabled true

# 配置跳过 SSL 证书验证（解决 MITM 代理问题）
scoop config aria2-options '--check-certificate=false'

# 关闭 aria2 警告提示
scoop config aria2-warning-enabled false
```

#### 验证配置

```powershell
scoop config
```

应该看到：

```
aria2-enabled  : True
aria2-options  : --check-certificate=false
```

### 配置后效果

配置完成后，scoop 将使用 aria2 下载所有软件包：
- 自动跳过 SSL 证书验证
- 多线程下载，速度更快
- 支持断点续传

```powershell
# 现在可以正常安装软件了
scoop install pandoc poppler qpdf tesseract
```

---

## 7. SSL 证书验证配置（无管理员权限）

### 问题背景

当系统缺少 USERTrust ECC 根证书，且没有管理员权限安装证书时，许多 HTTPS 连接会失败：

```
curl: (60) SSL certificate problem: unable to get local issuer certificate
The SSL connection could not be established
```

### 解决方案：跳过 SSL 证书验证

**安全警告**：跳过 SSL 验证会降低安全性，仅在受信任的网络环境中使用。

#### 自动配置（推荐）

运行 `setup.py` 会自动配置所有工具：

```powershell
python setup.py
```

#### 手动配置

**1. curl 配置**

创建 `~/.curlrc` 文件：

```
insecure
```

验证：
```powershell
curl https://github.com  # 不需要 -k 参数
```

**2. Git 配置**

```powershell
git config --global http.sslVerify false
```

验证：
```powershell
git config --global http.sslVerify  # 应输出 false
```

**3. npm 配置**

```powershell
npm config set strict-ssl false
```

验证：
```powershell
npm config get strict-ssl  # 应输出 false
```

**4. Node.js 配置**

在 PowerShell profile 中添加：

```powershell
$env:NODE_TLS_REJECT_UNAUTHORIZED = "0"
```

**5. Python 配置**

在 PowerShell profile 中添加：

```powershell
$env:PYTHONHTTPSVERIFY = "0"
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

如果能获得管理员权限，建议安装缺少的根证书：

```powershell
# 以管理员权限运行
Import-Certificate -FilePath "USERTrust_ECC_Root.crt" -CertStoreLocation Cert:\LocalMachine\Root
```

安装后可以移除上述跳过验证的配置。

---

## 8. 已知问题

### VS Code 终端 emoji 乱码

**原因**: VS Code 终端基于 xterm.js，在 Windows 上的 Unicode 处理有问题。

**解决方案**（本项目已集成）:

1. **使用支持 Emoji 的字体**: `Cascadia Mono`
2. **设置 Unicode 版本**: `terminal.integrated.unicodeVersion: "11"`
3. **终端启动时设置代码页**: `args: ["-NoExit", "-Command", "chcp 65001"]`
4. **关闭 GPU 加速**: `terminal.integrated.gpuAcceleration: "off"`

运行 `python setup.py` 会自动配置以上设置。

**字体安装**:
- Windows 10/11 通常已预装 Cascadia Mono
- 如未安装，可从 [GitHub Cascadia Code](https://github.com/microsoft/cascadia-code/releases) 下载

**仍有问题时**:
- 使用 Windows Terminal（`Ctrl + Shift + C` 打开外部终端）
- 重启 VS Code 和 Claude Code

相关 Issue:
- [xtermjs/xterm.js#2693](https://github.com/xtermjs/xterm.js/issues/2693)
- [microsoft/vscode#206468](https://github.com/microsoft/vscode/issues/206468)

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
- 用户级 UTF-8 环境变量（PYTHONUTF8、PYTHONIOENCODING、LANG，解决 pip 等工具编码问题）
- PowerShell Profile（代理检测/锁定、`proxy` 帮助命令、UTF-8 编码、SSL 环境变量）
- VS Code 设置（PowerShell 7 终端、Emoji 支持）
- Git Bash 配置（.minttyrc、.bash_profile UTF-8）
- SSL 证书验证跳过（curl/Git/npm，无管理员权限方案）
- Scoop aria2 下载器

**注意**：重复运行 `setup.py` 会自动更新已有配置（替换旧版本），不会跳过。

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
