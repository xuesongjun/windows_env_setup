# Windows 开发环境配置指南

本文档汇总了 Windows 下 PowerShell 7、VS Code、代理自动检测、UTF-8 编码等配置方法。

## 目录

- [1. 智能代理配置](#1-智能代理配置)
- [2. UTF-8 编码配置](#2-utf-8-编码配置)
- [3. VS Code 配置](#3-vs-code-配置)
- [4. Git Bash 配置](#4-git-bash-配置)
- [5. Scoop 与 aria2 配置](#5-scoop-与-aria2-配置)
- [6. SSL 证书验证配置（无管理员权限）](#6-ssl-证书验证配置无管理员权限)
- [7. Claude Code Skills 配置](#7-claude-code-skills-配置)
- [8. 已知问题](#8-已知问题)
- [9. 快速安装](#9-快速安装)

---

## 1. 智能代理配置

### 功能

- 启动 PowerShell 时自动检测 Windows 代理设置开关
- 代理开启时自动配置：环境变量、Git、Scoop、npm
- 代理关闭时自动清除所有代理配置

### 配置文件

**位置**: `$HOME\Documents\PowerShell\Microsoft.PowerShell_profile.ps1`

```powershell
# ========== 智能代理配置 ==========
$PROXY_HTTP = "http://127.0.0.1:33210"
$PROXY_SOCKS = "socks5://127.0.0.1:33211"
$PROXY_HOST_PORT = "127.0.0.1:33210"

function Set-AutoProxy {
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    $proxyEnable = (Get-ItemProperty -Path $regPath -Name ProxyEnable -ErrorAction SilentlyContinue).ProxyEnable

    if ($proxyEnable -eq 1) {
        # 设置当前会话环境变量
        $env:HTTP_PROXY = $PROXY_HTTP
        $env:HTTPS_PROXY = $PROXY_HTTP
        $env:ALL_PROXY = $PROXY_SOCKS

        # 设置用户级系统环境变量（对 Claude Code 等生效）
        [System.Environment]::SetEnvironmentVariable("HTTP_PROXY", $PROXY_HTTP, "User")
        [System.Environment]::SetEnvironmentVariable("HTTPS_PROXY", $PROXY_HTTP, "User")
        [System.Environment]::SetEnvironmentVariable("ALL_PROXY", $PROXY_SOCKS, "User")

        # 设置 Git/Scoop/npm 代理
        git config --global http.proxy $PROXY_HTTP 2>$null
        git config --global https.proxy $PROXY_HTTP 2>$null
        scoop config proxy $PROXY_HOST_PORT 2>$null
        npm config set proxy $PROXY_HTTP 2>$null
        npm config set https-proxy $PROXY_HTTP 2>$null

        Write-Host "[Proxy] Enabled: $PROXY_HTTP" -ForegroundColor Green
    } else {
        # 清除所有代理配置
        $env:HTTP_PROXY = $null
        $env:HTTPS_PROXY = $null
        $env:ALL_PROXY = $null
        [System.Environment]::SetEnvironmentVariable("HTTP_PROXY", $null, "User")
        [System.Environment]::SetEnvironmentVariable("HTTPS_PROXY", $null, "User")
        [System.Environment]::SetEnvironmentVariable("ALL_PROXY", $null, "User")
        git config --global --unset http.proxy 2>$null
        git config --global --unset https.proxy 2>$null
        scoop config rm proxy 2>$null
        npm config delete proxy 2>$null
        npm config delete https-proxy 2>$null

        Write-Host "[Proxy] Direct connection" -ForegroundColor Yellow
    }
}

# 启动时自动检测
Set-AutoProxy
```

### 可用命令

| 命令 | 功能 |
|------|------|
| `Set-AutoProxy` | 重新检测代理状态 |
| `Enable-Proxy` | 强制开启代理 |
| `Disable-Proxy` | 强制关闭代理 |
| `Get-ProxyStatus` | 查看当前状态 |

### 代理检测原理

读取 Windows 注册表中的代理开关状态：

```
HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings\ProxyEnable
- 值为 1：代理开启
- 值为 0：代理关闭
```

---

## 2. UTF-8 编码配置

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

| 环境变量 | 作用 | 生效范围 |
|---------|------|---------|
| `PYTHONUTF8=1` | Python 3.7+ UTF-8 模式，影响文件读写、`open()` 默认编码 | 用户级永久 |
| `PYTHONIOENCODING=utf-8` | 标准输入/输出/错误流的编码 | 用户级永久 |

### Python 脚本编码

在 Python 脚本开头添加：

```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
```

---

## 3. VS Code 配置

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

---

## 4. Git Bash 配置

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

## 5. Scoop 与 aria2 配置

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
   curl -x http://127.0.0.1:33210 https://github.com
   ```

**注意**：安装 CA 证书意味着信任该证书签发的所有证书，请确保只在受信任的环境中使用。

### 安装和配置

#### 步骤 1：安装 aria2

如果 scoop 已经出现 SSL 错误，需要手动下载 aria2：

```powershell
# 使用 curl 手动下载（-k 跳过证书验证）
curl -k -x http://127.0.0.1:33210 -L -o "$env:USERPROFILE/scoop/cache/aria2-temp.zip" "https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip"

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

## 6. SSL 证书验证配置（无管理员权限）

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

## 7. Claude Code Skills 配置

### Skills 目录结构

```
~/.claude/skills/
├── skill-name/
│   └── SKILL.md
```

### SKILL.md 格式

```markdown
---
name: skill-name
description: 简短描述（用于自动匹配）
---

# 标题

具体指令内容...

$ARGUMENTS
```

### 安装官方插件

```powershell
# 添加插件市场
claude plugin marketplace add anthropics/skills

# 安装插件
claude plugin install document-skills@anthropic-agent-skills
claude plugin install coderabbit@claude-plugins-official
```

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
- PowerShell Profile（代理检测、UTF-8 编码、SSL 环境变量）
- VS Code 设置（PowerShell 7 终端、Emoji 支持）
- Git Bash 配置（.minttyrc、.bash_profile UTF-8）
- SSL 证书验证跳过（curl/Git/npm，无管理员权限方案）
- Claude Code Skills 示例
- Scoop aria2 下载器

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
curl -k -x http://127.0.0.1:33210 -L -o "$env:USERPROFILE\scoop\apps\tesseract\current\tessdata\chi_sim.traineddata" "https://github.com/tesseract-ocr/tessdata_fast/raw/main/chi_sim.traineddata"
```

---

## 参考链接

- [PowerShell 7 下载](https://github.com/PowerShell/PowerShell/releases)
- [VS Code 设置](https://code.visualstudio.com/docs/getstarted/settings)
- [Claude Code Skills 文档](https://code.claude.com/docs/en/skills)
- [Scoop 包管理器](https://scoop.sh/)
- [aria2 项目](https://github.com/aria2/aria2)
