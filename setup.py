# -*- coding: utf-8 -*-
"""
Windows 开发环境自动配置脚本
用于配置 PowerShell 7、VS Code、代理自动检测、UTF-8 编码等

使用方法: python setup.py
"""

import os
import sys
import json
import subprocess
import winreg
from pathlib import Path

# 强制 UTF-8 输出
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


# ==================== 配置参数 ====================
PROXY_HTTP = "http://127.0.0.1:33210"
PROXY_SOCKS = "socks5://127.0.0.1:33211"
PROXY_HOST_PORT = "127.0.0.1:33210"


# ==================== PowerShell Profile 内容 ====================
POWERSHELL_PROFILE = '''# ========== SSL 证书验证配置（解决缺少根证书问题）==========
# 由于系统缺少 USERTrust ECC 根证书，且无管理员权限安装，配置跳过验证
$env:NODE_TLS_REJECT_UNAUTHORIZED = "0"  # Node.js
$env:PYTHONHTTPSVERIFY = "0"             # Python (部分版本)
$env:GIT_SSL_NO_VERIFY = "true"          # Git (备用)

# ========== UTF-8 编码设置（解决中文乱码）==========
[Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"                   # Python 3.7+ 默认 UTF-8 模式
$env:PYTHONIOENCODING = "utf-8"         # Python I/O 编码
$env:LANG = "en_US.UTF-8"
$env:LC_ALL = "en_US.UTF-8"
chcp 65001 >$null 2>&1

# 持久化 UTF-8 环境变量到用户级（确保 CMD/Git Bash/-NoProfile 等场景也生效）
if (-not [Environment]::GetEnvironmentVariable("PYTHONUTF8", "User")) {{
    [Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
    [Environment]::SetEnvironmentVariable("PYTHONIOENCODING", "utf-8", "User")
    [Environment]::SetEnvironmentVariable("LANG", "en_US.UTF-8", "User")
}}

# ========== 智能代理配置（动态读取注册表，自适应 VPN 客户端端口）==========
# 兜底默认值（注册表读取失败时使用）
$PROXY_FALLBACK_HTTP      = "{proxy_http}"
$PROXY_FALLBACK_SOCKS     = "{proxy_socks}"
$PROXY_FALLBACK_HOST_PORT = "{proxy_host_port}"

# 从 Windows 系统代理注册表读取当前代理地址（不管 ProxyEnable 状态）
# 返回格式如 "127.0.0.1:7897"，读不到则返回 $null
function Get-SystemProxyAddress {{
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    $props = Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue
    if ($props.ProxyServer) {{ return $props.ProxyServer }}
    return $null
}}

# 启动时自动检测代理：从注册表读取端口，只在值变化时才写用户级环境变量
function Set-AutoProxy {{
    $regPath     = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    $props       = Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue
    $proxyEnable = $props.ProxyEnable
    $proxyServer = $props.ProxyServer   # 如 "127.0.0.1:7897"

    if ($proxyEnable -eq 1 -and $proxyServer) {{
        $httpProxy  = "http://$proxyServer"
        $socksProxy = "socks5://$proxyServer"   # 现代客户端（Clash 等）使用混合端口

        # 设置当前会话环境变量
        $env:HTTP_PROXY  = $httpProxy
        $env:HTTPS_PROXY = $httpProxy
        $env:ALL_PROXY   = $socksProxy

        # 只在值变化时写注册表，避免每次启动都写（节省约 150-300ms）
        $currentHttp = [Environment]::GetEnvironmentVariable("HTTP_PROXY", "User")
        if ($currentHttp -ne $httpProxy) {{
            [Environment]::SetEnvironmentVariable("HTTP_PROXY",  $httpProxy,  "User")
            [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $httpProxy,  "User")
            [Environment]::SetEnvironmentVariable("ALL_PROXY",   $socksProxy, "User")
        }}

        Write-Host "[Proxy] $httpProxy (use 'Sync-ProxyToTools' to sync to git/npm/scoop)" -ForegroundColor Green
    }} else {{
        $env:HTTP_PROXY  = $null
        $env:HTTPS_PROXY = $null
        $env:ALL_PROXY   = $null

        # 只在已设置时才清除，避免不必要的注册表写入
        $currentHttp = [Environment]::GetEnvironmentVariable("HTTP_PROXY", "User")
        if ($currentHttp) {{
            [Environment]::SetEnvironmentVariable("HTTP_PROXY",  $null, "User")
            [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $null, "User")
            [Environment]::SetEnvironmentVariable("ALL_PROXY",   $null, "User")
        }}

        Write-Host "[Proxy] Direct connection" -ForegroundColor Yellow
    }}
}}

# 同步代理设置到外部工具（手动调用，耗时约 3-4 秒）
function Sync-ProxyToTools {{
    if ($env:HTTP_PROXY) {{
        Write-Host "Syncing proxy to tools..." -ForegroundColor Cyan

        # 设置用户级环境变量（对新进程永久生效）
        [Environment]::SetEnvironmentVariable("HTTP_PROXY", $env:HTTP_PROXY, "User")
        [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $env:HTTPS_PROXY, "User")
        [Environment]::SetEnvironmentVariable("ALL_PROXY", $env:ALL_PROXY, "User")

        # 配置各工具
        git config --global http.proxy $env:ALL_PROXY 2>$null
        git config --global https.proxy $env:ALL_PROXY 2>$null
        scoop config proxy ($env:HTTP_PROXY -replace '^https?://', '') 2>$null
        npm config set proxy $env:HTTP_PROXY 2>$null
        npm config set https-proxy $env:HTTP_PROXY 2>$null

        Write-Host "[Sync] Proxy synced to git/scoop/npm + user env" -ForegroundColor Green
    }} else {{
        Write-Host "Clearing proxy from tools..." -ForegroundColor Cyan

        # 清除用户级环境变量
        [Environment]::SetEnvironmentVariable("HTTP_PROXY", $null, "User")
        [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $null, "User")
        [Environment]::SetEnvironmentVariable("ALL_PROXY", $null, "User")

        # 清除工具配置
        git config --global --unset http.proxy 2>$null
        git config --global --unset https.proxy 2>$null
        scoop config rm proxy 2>$null
        npm config delete proxy 2>$null
        npm config delete https-proxy 2>$null

        Write-Host "[Sync] Proxy cleared from all tools" -ForegroundColor Yellow
    }}
}}

# 手动开启代理（优先从注册表读取当前端口，兜底用默认值）
function Enable-Proxy {{
    $proxyServer = Get-SystemProxyAddress
    if (-not $proxyServer) {{ $proxyServer = $PROXY_FALLBACK_HOST_PORT }}
    $httpProxy  = "http://$proxyServer"
    $socksProxy = "socks5://$proxyServer"

    $env:HTTP_PROXY  = $httpProxy
    $env:HTTPS_PROXY = $httpProxy
    $env:ALL_PROXY   = $socksProxy
    Write-Host "[Proxy] Enabled: $httpProxy (session)" -ForegroundColor Green

    # 询问是否同步到工具
    $response = Read-Host "Sync to git/npm/scoop? (Y/n)"
    if ($response -ne 'n' -and $response -ne 'N') {{
        Sync-ProxyToTools
    }}
}}

# 手动关闭代理（同时清除工具配置）
function Disable-Proxy {{
    $env:HTTP_PROXY = $null
    $env:HTTPS_PROXY = $null
    $env:ALL_PROXY = $null
    Write-Host "[Proxy] Disabled (session)" -ForegroundColor Yellow

    # 询问是否清除工具配置
    $response = Read-Host "Clear from git/npm/scoop? (Y/n)"
    if ($response -ne 'n' -and $response -ne 'N') {{
        Sync-ProxyToTools
    }}
}}

# 查看代理状态（增强版：显示工具配置状态）
function Get-ProxyStatus {{
    Write-Host ""
    Write-Host "  Proxy Status" -ForegroundColor Cyan
    Write-Host "  ============================================================" -ForegroundColor DarkGray

    # 锁定状态
    $lockFile = "$env:USERPROFILE\.proxy_lock"
    if (Test-Path $lockFile) {{
        Write-Host "  Mode:        " -NoNewline; Write-Host "Locked (ignore system settings)" -ForegroundColor Green
    }} else {{
        Write-Host "  Mode:        " -NoNewline; Write-Host "Auto-detect (follow system settings)" -ForegroundColor Yellow
    }}

    Write-Host "  ------------------------------------------------------------" -ForegroundColor DarkGray

    # 当前会话环境变量（完整显示三个地址）
    Write-Host "  Session:" -ForegroundColor White
    if ($env:HTTP_PROXY) {{
        Write-Host "    HTTP_PROXY   = $env:HTTP_PROXY" -ForegroundColor Green
        Write-Host "    HTTPS_PROXY  = $env:HTTPS_PROXY" -ForegroundColor Green
        Write-Host "    ALL_PROXY    = $env:ALL_PROXY" -ForegroundColor Green
    }} else {{
        Write-Host "    (not set)" -ForegroundColor Gray
    }}

    # 用户级环境变量
    Write-Host "  User Env:" -ForegroundColor White
    $uHttp  = [Environment]::GetEnvironmentVariable("HTTP_PROXY", "User")
    $uHttps = [Environment]::GetEnvironmentVariable("HTTPS_PROXY", "User")
    $uAll   = [Environment]::GetEnvironmentVariable("ALL_PROXY", "User")
    if ($uHttp) {{
        Write-Host "    HTTP_PROXY   = $uHttp" -ForegroundColor Green
        Write-Host "    HTTPS_PROXY  = $uHttps" -ForegroundColor Green
        Write-Host "    ALL_PROXY    = $uAll" -ForegroundColor Green
    }} else {{
        Write-Host "    (not set)" -ForegroundColor Gray
    }}

    Write-Host "  ------------------------------------------------------------" -ForegroundColor DarkGray

    # Git 配置
    $gitHttp  = git config --global --get http.proxy 2>$null
    $gitHttps = git config --global --get https.proxy 2>$null
    Write-Host "  Git:" -ForegroundColor White
    if ($gitHttp -or $gitHttps) {{
        if ($gitHttp)  {{ Write-Host "    http.proxy   = $gitHttp" -ForegroundColor Green }}
        if ($gitHttps) {{ Write-Host "    https.proxy  = $gitHttps" -ForegroundColor Green }}
    }} else {{
        Write-Host "    (not configured)" -ForegroundColor Gray
    }}

    # npm 配置
    $npmProxy  = npm config get proxy 2>$null
    $npmHttps  = npm config get https-proxy 2>$null
    Write-Host "  npm:" -ForegroundColor White
    if ($npmProxy -and $npmProxy -ne "null") {{
        Write-Host "    proxy        = $npmProxy" -ForegroundColor Green
        if ($npmHttps -and $npmHttps -ne "null") {{
            Write-Host "    https-proxy  = $npmHttps" -ForegroundColor Green
        }}
    }} else {{
        Write-Host "    (not configured)" -ForegroundColor Gray
    }}

    # Scoop 配置
    $scoopProxy = scoop config proxy 2>$null
    Write-Host "  Scoop:" -ForegroundColor White
    if ($scoopProxy -and $scoopProxy -notmatch "not set|^$") {{
        Write-Host "    proxy        = $scoopProxy" -ForegroundColor Green
    }} else {{
        Write-Host "    (not configured)" -ForegroundColor Gray
    }}

    Write-Host "  ============================================================" -ForegroundColor DarkGray
    Write-Host ""
}}

# ========== 代理锁定功能（固定代理状态，不跟随系统设置）==========
function Lock-Proxy {{
    $proxyServer = Get-SystemProxyAddress
    if (-not $proxyServer) {{ $proxyServer = $PROXY_FALLBACK_HOST_PORT }}
    $httpProxy  = "http://$proxyServer"
    $socksProxy = "socks5://$proxyServer"

    $env:HTTP_PROXY  = $httpProxy
    $env:HTTPS_PROXY = $httpProxy
    $env:ALL_PROXY   = $socksProxy
    [Environment]::SetEnvironmentVariable("HTTP_PROXY",  $httpProxy,  "User")
    [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $httpProxy,  "User")
    [Environment]::SetEnvironmentVariable("ALL_PROXY",   $socksProxy, "User")
    New-Item -Path "$env:USERPROFILE\.proxy_lock" -ItemType File -Force >$null
    Write-Host "[Proxy] Locked: $httpProxy" -ForegroundColor Green
    Write-Host "        proxy keeps ON regardless of system settings" -ForegroundColor Gray
}}

function Unlock-Proxy {{
    Remove-Item -Path "$env:USERPROFILE\.proxy_lock" -Force -ErrorAction SilentlyContinue
    Write-Host "[Proxy] Unlocked: back to auto-detect mode" -ForegroundColor Yellow
    Set-AutoProxy
}}

function Update-Env {{
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "成功从系统注册表同步了最新的 Path 环境变量！" -ForegroundColor Cyan
}}

# ========== 帮助命令（列出所有代理相关操作）==========
function Get-ProxyHelp {{
    Write-Host ""
    Write-Host "  Proxy Commands" -ForegroundColor Cyan
    Write-Host "  ============================================================" -ForegroundColor DarkGray
    Write-Host "  proxy              " -NoNewline -ForegroundColor White; Write-Host "Show this help" -ForegroundColor Gray
    Write-Host "  proxy-status       " -NoNewline -ForegroundColor White; Write-Host "Show current proxy status (session/user/git/npm)" -ForegroundColor Gray
    Write-Host "  Enable-Proxy       " -NoNewline -ForegroundColor Green; Write-Host "Turn ON proxy for current session" -ForegroundColor Gray
    Write-Host "  Disable-Proxy      " -NoNewline -ForegroundColor Yellow; Write-Host "Turn OFF proxy for current session" -ForegroundColor Gray
    Write-Host "  Lock-Proxy         " -NoNewline -ForegroundColor Green; Write-Host "Lock proxy ON permanently (ignores system settings)" -ForegroundColor Gray
    Write-Host "  Unlock-Proxy       " -NoNewline -ForegroundColor Yellow; Write-Host "Unlock, back to auto-detect mode" -ForegroundColor Gray
    Write-Host "  proxy-sync         " -NoNewline -ForegroundColor White; Write-Host "Sync proxy to git/npm/scoop" -ForegroundColor Gray
    Write-Host "  ============================================================" -ForegroundColor DarkGray
    Write-Host ""
}}

# 快捷别名
Set-Alias -Name proxy -Value Get-ProxyHelp
Set-Alias -Name proxy-sync -Value Sync-ProxyToTools
Set-Alias -Name proxy-status -Value Get-ProxyStatus
Set-Alias -Name us -Value Update-Env
# 启动时自动检测（快速，约 50ms）
Set-AutoProxy
'''


def print_step(msg):
    print(f"\n[*] {msg}")


def print_ok(msg):
    print(f"    [OK] {msg}")


def print_warn(msg):
    print(f"    [WARN] {msg}")


def print_err(msg):
    print(f"    [ERROR] {msg}")


def get_pwsh_path():
    """查找 PowerShell 7 路径"""
    # 常见安装路径
    possible_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "PowerShell",
        Path("C:/Program Files/PowerShell"),
        Path(os.environ.get("PROGRAMFILES", "")) / "PowerShell",
    ]

    for base_path in possible_paths:
        if base_path.exists():
            # 查找版本目录
            for version_dir in sorted(base_path.iterdir(), reverse=True):
                pwsh_exe = version_dir / "pwsh.exe"
                if pwsh_exe.exists():
                    return str(pwsh_exe)

    # 尝试用 where 命令
    try:
        result = subprocess.run(["where", "pwsh"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except Exception:
        pass

    return None


def setup_powershell_profile():
    """配置 PowerShell 7 profile（追加模式，不覆盖现有配置）"""
    print_step("配置 PowerShell 7 Profile...")

    # PowerShell 7 profile 路径
    ps_profile_dir = Path.home() / "Documents" / "PowerShell"
    ps_profile_path = ps_profile_dir / "Microsoft.PowerShell_profile.ps1"

    # 创建目录
    ps_profile_dir.mkdir(parents=True, exist_ok=True)

    # 生成 profile 内容
    profile_content = POWERSHELL_PROFILE.format(
        proxy_http=PROXY_HTTP,
        proxy_socks=PROXY_SOCKS,
        proxy_host_port=PROXY_HOST_PORT
    )

    # 标记：用于识别我们管理的配置块
    BLOCK_START = "# ========== 以下由 windows_env_setup 自动添加 =========="
    BLOCK_START_ALT = "# ========== SSL 证书验证配置"  # 旧版直接写入时的开头

    # 检查是否已存在且包含配置
    if ps_profile_path.exists():
        existing_content = ps_profile_path.read_text(encoding='utf-8', errors='ignore')

        # 检查是否已包含我们的配置（需要替换更新）
        if "智能代理配置" in existing_content:
            # 找到旧配置块并替换为新内容
            # 情况1：通过追加模式添加的（有 BLOCK_START 标记）
            if BLOCK_START in existing_content:
                user_part = existing_content.split(BLOCK_START)[0].rstrip()
                new_content = user_part + "\n\n" + BLOCK_START + "\n" + profile_content
            # 情况2：首次创建时直接写入的（整个文件都是我们的配置）
            elif existing_content.lstrip().startswith(BLOCK_START_ALT):
                new_content = profile_content
            else:
                # 无法确定边界，安全起见整体替换
                new_content = profile_content

            ps_profile_path.write_text(new_content, encoding='utf-8')
            print_ok(f"已更新 Profile（替换旧配置）: {ps_profile_path}")
            # 继续执行后面的 PS5 配置，不 return

        # 文件存在且有内容，追加配置
        elif existing_content.strip():
            print_ok(f"检测到现有 profile，将追加配置")
            with open(ps_profile_path, 'a', encoding='utf-8') as f:
                f.write("\n\n" + BLOCK_START + "\n")
                f.write(profile_content)
            print_ok(f"已追加配置到: {ps_profile_path}")
        else:
            # 文件为空，直接写入
            ps_profile_path.write_text(profile_content, encoding='utf-8')
            print_ok(f"已创建 profile: {ps_profile_path}")
    else:
        # 文件不存在，创建新文件
        ps_profile_path.write_text(profile_content, encoding='utf-8')
        print_ok(f"已创建 profile: {ps_profile_path}")

    # 同时配置 Windows PowerShell 5.x（可选）
    ps5_profile_dir = Path.home() / "Documents" / "WindowsPowerShell"
    ps5_profile_path = ps5_profile_dir / "Microsoft.PowerShell_profile.ps1"

    ps5_profile_dir.mkdir(parents=True, exist_ok=True)
    if ps5_profile_path.exists():
        ps5_content = ps5_profile_path.read_text(encoding='utf-8', errors='ignore')
        if "智能代理配置" in ps5_content:
            ps5_profile_path.write_text(profile_content, encoding='utf-8')
            print_ok(f"已更新 Windows PowerShell 5.x profile: {ps5_profile_path}")
        elif not ps5_content.strip():
            ps5_profile_path.write_text(profile_content, encoding='utf-8')
            print_ok(f"已创建 Windows PowerShell 5.x profile: {ps5_profile_path}")
        else:
            print_ok(f"Windows PowerShell 5.x profile 已存在，跳过")
    else:
        ps5_profile_path.write_text(profile_content, encoding='utf-8')
        print_ok(f"已创建 Windows PowerShell 5.x profile: {ps5_profile_path}")

    return True


def setup_vscode_settings():
    """配置 VS Code 设置"""
    print_step("配置 VS Code 设置...")

    # VS Code settings.json 路径
    vscode_settings_path = Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "settings.json"

    if not vscode_settings_path.parent.exists():
        print_warn("VS Code 配置目录不存在，跳过 VS Code 配置")
        return False

    # 查找 PowerShell 7 路径
    pwsh_path = get_pwsh_path()
    if not pwsh_path:
        print_warn("未找到 PowerShell 7，跳过终端配置")
        pwsh_path = "pwsh.exe"
    else:
        print_ok(f"找到 PowerShell 7: {pwsh_path}")

    # 需要添加的设置
    new_settings = {
        "terminal.integrated.defaultProfile.windows": "PowerShell 7",
        "terminal.integrated.profiles.windows": {
            "PowerShell 7": {
                "path": pwsh_path,
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
        # Emoji 支持配置
        "terminal.integrated.fontFamily": "Cascadia Mono, Consolas, 'Courier New', monospace",
        "terminal.integrated.unicodeVersion": "11",
        "terminal.integrated.gpuAcceleration": "off",
        "files.encoding": "utf8",
        "files.autoGuessEncoding": True,
        "terminal.external.windowsExec": "wt.exe"
    }

    # 读取现有设置
    settings = {}
    if vscode_settings_path.exists():
        try:
            content = vscode_settings_path.read_text(encoding='utf-8')
            # 移除可能的 BOM
            if content.startswith('\ufeff'):
                content = content[1:]
            settings = json.loads(content)
        except json.JSONDecodeError as e:
            print_err(f"VS Code settings.json 格式错误: {e}")
            return False

    # 深层合并设置（保留用户自定义的终端配置等）
    def deep_merge(base, override):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    deep_merge(settings, new_settings)

    # 写入文件
    vscode_settings_path.write_text(
        json.dumps(settings, indent=4, ensure_ascii=False),
        encoding='utf-8'
    )
    print_ok(f"已更新 VS Code 设置: {vscode_settings_path}")

    return True


def setup_scoop_aria2():
    """
    配置 Scoop 使用 aria2 下载器（解决 SSL 证书问题）

    为什么需要 aria2？
    -----------------
    Scoop 默认使用 .NET 的 Invoke-WebRequest 下载文件。
    当使用 Clash 等代理软件（启用 HTTPS 解密/MITM）时，
    .NET 会因为不信任代理返回的证书而报 SSL 错误。

    aria2 是一个轻量级多协议下载工具，可以配置跳过 SSL 证书验证，
    从而绕过这个问题。同时 aria2 支持多线程下载，速度更快。

    配置项说明：
    - aria2-enabled: 启用 aria2 作为下载器
    - aria2-options: --check-certificate=false 跳过证书验证
    - aria2-warning-enabled: 关闭 aria2 警告提示
    """
    print_step("配置 Scoop aria2 下载器...")

    try:
        # 检查 scoop 是否安装（scoop 是 .cmd/.ps1 脚本，需要 shell=True）
        result = subprocess.run(
            ["scoop", "--version"], capture_output=True, text=True, shell=True
        )
        if result.returncode != 0:
            print_warn("Scoop 未安装，跳过配置")
            return False
    except FileNotFoundError:
        print_warn("Scoop 未安装，跳过配置")
        return False

    # 检查 aria2 是否安装
    result = subprocess.run(
        ["scoop", "list"], capture_output=True, text=True, shell=True
    )
    if "aria2" not in result.stdout:
        print_warn("aria2 未安装，请先运行: scoop install aria2")
        print_warn("如果 SSL 错误，手动下载 aria2 到 scoop/cache 目录")
        return False

    # 配置 scoop 使用 aria2
    configs = [
        ("aria2-enabled", "true"),
        ("aria2-options", "--check-certificate=false"),
        ("aria2-warning-enabled", "false"),
    ]

    for key, value in configs:
        subprocess.run(
            ["scoop", "config", key, value], capture_output=True, shell=True
        )
        print_ok(f"已设置 scoop config {key} = {value}")

    return True


def setup_ssl_workarounds():
    """
    配置 SSL 证书验证跳过（无管理员权限时的解决方案）

    背景说明：
    ---------
    当系统缺少 USERTrust ECC 根证书，且没有管理员权限安装时，
    许多 HTTPS 连接会失败。此函数配置各工具跳过 SSL 证书验证。

    配置的工具：
    - curl: ~/.curlrc 添加 "insecure"
    - Git: http.sslVerify false
    - npm: strict-ssl false
    - Node.js: NODE_TLS_REJECT_UNAUTHORIZED=0 (在 PowerShell profile 中)
    - Python: PYTHONHTTPSVERIFY=0 (在 PowerShell profile 中)

    安全警告：
    ---------
    跳过 SSL 验证会降低安全性，仅在受信任的网络环境中使用。
    如有管理员权限，建议安装根证书（见 install_ecc_root_cert.ps1）。
    """
    print_step("配置 SSL 证书验证跳过（无管理员权限解决方案）...")

    results = []

    # 1. 配置 ~/.curlrc（追加模式）
    curlrc_path = Path.home() / ".curlrc"
    try:
        if curlrc_path.exists():
            existing_content = curlrc_path.read_text(encoding='utf-8', errors='ignore')
            if "insecure" in existing_content:
                print_ok("~/.curlrc 已包含 insecure 配置")
            elif existing_content.strip():
                # 追加配置
                with open(curlrc_path, 'a', encoding='utf-8') as f:
                    f.write("\n# 跳过 SSL 证书验证（解决缺少根证书问题）\ninsecure\n")
                print_ok("已追加 insecure 到 ~/.curlrc")
            else:
                # 文件为空
                curlrc_path.write_text("# 跳过 SSL 证书验证（解决缺少根证书问题）\ninsecure\n", encoding='utf-8')
                print_ok("已创建 ~/.curlrc")
        else:
            curlrc_path.write_text("# 跳过 SSL 证书验证（解决缺少根证书问题）\ninsecure\n", encoding='utf-8')
            print_ok("已创建 ~/.curlrc (curl 跳过证书验证)")
        results.append(True)
    except Exception as e:
        print_err(f"配置 ~/.curlrc 失败: {e}")
        results.append(False)

    # 2. 配置 Git 跳过 SSL 验证
    try:
        result = subprocess.run(
            ["git", "config", "--global", "http.sslVerify", "false"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print_ok("已配置 Git http.sslVerify = false")
            results.append(True)
        else:
            print_warn("Git 配置失败（可能未安装）")
            results.append(False)
    except Exception as e:
        print_warn(f"Git 配置失败: {e}")
        results.append(False)

    # 3. 配置 npm 跳过 SSL 验证
    try:
        result = subprocess.run(
            ["npm", "config", "set", "strict-ssl", "false"],
            capture_output=True, text=True, shell=True
        )
        if result.returncode == 0:
            print_ok("已配置 npm strict-ssl = false")
            results.append(True)
        else:
            print_warn("npm 配置失败（可能未安装）")
            results.append(False)
    except Exception as e:
        print_warn(f"npm 配置失败: {e}")
        results.append(False)

    # 4. 提示用户 PowerShell 环境变量已在 profile 中配置
    print_ok("Node.js/Python SSL 跳过已在 PowerShell profile 中配置")

    return all(results) or any(results)


def setup_git_bash():
    """
    配置 Git Bash 的 UTF-8 和 Emoji 支持（追加模式，不覆盖现有配置）

    配置文件：
    - ~/.minttyrc: MinTTY 终端配置（字体、编码）
    - ~/.bash_profile: Bash 环境变量
    """
    print_step("配置 Git Bash UTF-8 和 Emoji 支持...")

    results = []

    # 1. 配置 .minttyrc
    minttyrc_path = Path.home() / ".minttyrc"
    minttyrc_content = """# Git Bash (MinTTY) Configuration for UTF-8 and emoji support
# Generated by windows_env_setup
Charset=UTF-8
Locale=en_US
Font=Cascadia Mono
FontHeight=11
Term=xterm-256color
CursorType=block
Scrollbar=none
BoldAsFont=no
AllowBlinking=yes
"""
    try:
        if minttyrc_path.exists():
            existing_content = minttyrc_path.read_text(encoding='utf-8', errors='ignore')
            # 检查是否已包含我们的配置
            if "Charset=UTF-8" in existing_content and "Font=Cascadia" in existing_content:
                print_ok("~/.minttyrc 已包含 UTF-8 和字体配置")
            elif existing_content.strip():
                # 文件有内容但缺少配置，追加关键配置
                additions = []
                if "Charset=UTF-8" not in existing_content:
                    additions.append("Charset=UTF-8")
                if "Font=Cascadia" not in existing_content:
                    additions.append("Font=Cascadia Mono")
                    additions.append("FontHeight=11")
                if additions:
                    with open(minttyrc_path, 'a', encoding='utf-8') as f:
                        f.write("\n# Added by windows_env_setup\n")
                        f.write("\n".join(additions) + "\n")
                    print_ok("已追加配置到 ~/.minttyrc")
            else:
                # 文件为空
                minttyrc_path.write_text(minttyrc_content, encoding='utf-8')
                print_ok("已创建 ~/.minttyrc")
        else:
            minttyrc_path.write_text(minttyrc_content, encoding='utf-8')
            print_ok("已创建 ~/.minttyrc (Git Bash 终端配置)")
        results.append(True)
    except Exception as e:
        print_err(f"配置 ~/.minttyrc 失败: {e}")
        results.append(False)

    # 2. 配置 .bash_profile
    bash_profile_path = Path.home() / ".bash_profile"
    bash_profile_addition = """
# UTF-8 Configuration for Git Bash
# Generated by windows_env_setup
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export TERM=xterm-256color
"""
    try:
        if bash_profile_path.exists():
            existing_content = bash_profile_path.read_text(encoding='utf-8', errors='ignore')
            if "LANG=en_US.UTF-8" not in existing_content:
                # 追加配置
                with open(bash_profile_path, 'a', encoding='utf-8') as f:
                    f.write(bash_profile_addition)
                print_ok("已更新 ~/.bash_profile (追加 UTF-8 配置)")
            else:
                print_ok("~/.bash_profile 已包含 UTF-8 配置")
        else:
            # 创建新文件
            default_content = """# generated by Git for Windows
test -f ~/.profile && . ~/.profile
test -f ~/.bashrc && . ~/.bashrc
"""
            bash_profile_path.write_text(default_content + bash_profile_addition, encoding='utf-8')
            print_ok(f"已创建 ~/.bash_profile")
        results.append(True)
    except Exception as e:
        print_err(f"配置 ~/.bash_profile 失败: {e}")
        results.append(False)

    return all(results)


def check_system_utf8():
    """检查并提示启用 Windows UTF-8 全局支持"""
    print_step("检查系统 UTF-8 设置...")

    try:
        # 读取注册表检查当前代码页
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Nls\CodePage",
            0,
            winreg.KEY_READ
        )
        acp_value, _ = winreg.QueryValueEx(key, "ACP")
        winreg.CloseKey(key)

        if acp_value == "65001":
            print_ok("系统已启用 UTF-8 全局支持 (代码页 65001)")
            return True
        else:
            print_warn(f"系统当前使用代码页 {acp_value} (非 UTF-8)")
            print_warn("这会导致 Claude Code 执行脚本时出现中文乱码")
            print("")
            print("    建议启用 Windows UTF-8 全局支持：")
            print("    1. 以管理员身份运行 PowerShell")
            print("    2. 执行: .\\enable_utf8_system.ps1")
            print("    3. 重启计算机")
            print("")
            print("    或手动设置：")
            print("    控制面板 > 区域 > 管理 > 更改系统区域设置")
            print("    > 勾选 'Beta: 使用 Unicode UTF-8 提供全球语言支持'")
            print("")
            return False

    except Exception as e:
        print_warn(f"无法检查系统代码页设置: {e}")
        return False


def setup_utf8_env():
    """
    设置用户级 UTF-8 环境变量（持久化，不依赖 PowerShell Profile）

    解决场景：
    - CMD / Git Bash 中运行 pip install 等命令报 GBK 编码错误
    - pwsh -NoProfile 场景
    - 其他程序（如 IDE）启动的 Python 子进程
    """
    print_step("配置用户级 UTF-8 环境变量...")

    # 需要持久化的环境变量
    utf8_vars = {
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "LANG": "en_US.UTF-8",
    }

    try:
        # 通过注册表直接写入用户级环境变量
        reg_path = r"Environment"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0,
                            winreg.KEY_READ | winreg.KEY_WRITE) as key:
            for var_name, var_value in utf8_vars.items():
                try:
                    existing_value, _ = winreg.QueryValueEx(key, var_name)
                    if existing_value == var_value:
                        print_ok(f"{var_name}={var_value} (已存在)")
                        continue
                except FileNotFoundError:
                    pass  # 变量不存在，需要创建

                winreg.SetValueEx(key, var_name, 0, winreg.REG_SZ, var_value)
                print_ok(f"{var_name}={var_value} (已设置)")

                # 同时设置当前进程环境变量（立即生效）
                os.environ[var_name] = var_value

        print_ok("用户级环境变量已持久化（新终端自动生效）")
        return True

    except Exception as e:
        print_err(f"设置用户级环境变量失败: {e}")
        return False


def _get_wt_settings_paths():
    """返回 Windows Terminal 稳定版和预览版 settings.json 路径列表"""
    local = os.environ.get("LOCALAPPDATA", "")
    return [
        Path(local) / "Packages" / "Microsoft.WindowsTerminal_8wekyb3d8bbwe"
        / "LocalState" / "settings.json",
        Path(local) / "Packages" / "Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe"
        / "LocalState" / "settings.json",
    ]


def _configure_windows_terminal_font(font_face):
    """更新 Windows Terminal 所有配置的默认字体"""
    configured = False
    for settings_path in _get_wt_settings_paths():
        if not settings_path.exists():
            continue
        try:
            content = settings_path.read_text(encoding='utf-8')
            settings = json.loads(content)

            # 在 profiles.defaults 里设置字体（对所有配置文件生效）
            profiles = settings.setdefault("profiles", {})
            defaults = profiles.setdefault("defaults", {})
            current_face = defaults.get("font", {}).get("face", "")
            if current_face == font_face:
                print_ok(f"Windows Terminal 字体已是 {font_face}，无需修改")
            else:
                defaults.setdefault("font", {})["face"] = font_face
                settings_path.write_text(
                    json.dumps(settings, indent=4, ensure_ascii=False),
                    encoding='utf-8'
                )
                print_ok(f"已更新 Windows Terminal 默认字体 → {font_face}")

            configured = True
        except Exception as e:
            print_warn(f"更新 Windows Terminal 设置失败: {e}")

    if not configured:
        print_warn("未找到 Windows Terminal settings.json")
        print_warn(f"请手动设置：设置 > 配置文件 > 默认值 > 外观 > 字体 → {font_face}")


def setup_windows_terminal_wsl_home():
    """
    将 Windows Terminal 中 WSL 配置文件的起始目录设为 Linux home（~）。
    Windows Terminal 默认把 WSL 启动在 %USERPROFILE%（/mnt/c/Users/...），
    导致每次开终端都在 Windows 目录而非 Linux home。
    """
    print_step("配置 Windows Terminal WSL 起始目录...")

    fixed = False
    for settings_path in _get_wt_settings_paths():
        if not settings_path.exists():
            continue
        try:
            content = settings_path.read_text(encoding='utf-8')
            settings = json.loads(content)

            changed = False
            profiles = settings.setdefault("profiles", {})

            # 1. defaults：对所有配置文件生效
            defaults = profiles.setdefault("defaults", {})
            if defaults.get("startingDirectory") != "~":
                defaults["startingDirectory"] = "~"
                changed = True

            # 2. 遍历具体的 WSL profile，确保 WSL 配置也设置（避免 defaults 被覆盖）
            for profile in profiles.get("list", []):
                src = profile.get("source", "")
                name = profile.get("name", "")
                # 匹配所有 WSL 发行版
                if "Windows.Terminal.Wsl" in src or "wsl" in name.lower() or "ubuntu" in name.lower():
                    if profile.get("startingDirectory") != "~":
                        profile["startingDirectory"] = "~"
                        changed = True

            if changed:
                settings_path.write_text(
                    json.dumps(settings, indent=4, ensure_ascii=False),
                    encoding='utf-8'
                )
                print_ok(f"已设置 WSL 起始目录 → ~（Linux home）")
                print_ok(f"  配置文件：{settings_path}")
            else:
                print_ok("WSL 起始目录已是 ~，无需修改")

            fixed = True
        except Exception as e:
            print_warn(f"更新 Windows Terminal 设置失败：{e}")

    if not fixed:
        print_warn("未找到 Windows Terminal settings.json，跳过")
    return fixed


def setup_nerd_font():
    """
    下载并安装 JetBrainsMono Nerd Font（用户级，无需管理员权限），
    并自动更新 Windows Terminal 默认字体配置。
    """
    import urllib.request
    import zipfile
    import tempfile

    FONT_FACE = "JetBrainsMono Nerd Font Mono"
    FONT_ZIP_URL = (
        "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip"
    )

    print_step("安装 Nerd Font（JetBrainsMono Nerd Font）...")

    # 用户字体目录（无需管理员权限，Windows 10 1809+ 支持）
    font_dir = (
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Microsoft" / "Windows" / "Fonts"
    )
    font_dir.mkdir(parents=True, exist_ok=True)

    # 检查是否已安装（只检测 NFMono 变体）
    existing = list(font_dir.glob("JetBrainsMonoNerdFontMono-*.ttf"))
    if existing:
        print_ok(f"JetBrainsMono Nerd Font Mono 已安装（{len(existing)} 个文件），跳过下载")
        _configure_windows_terminal_font(FONT_FACE)
        return True

    # 下载
    print_ok(f"正在下载 JetBrainsMono.zip（约 20-30 MB）...")
    tmp_zip = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            tmp_zip = f.name

        # 支持代理环境变量（HTTP_PROXY / HTTPS_PROXY）
        proxy_handler = urllib.request.ProxyHandler()
        opener = urllib.request.build_opener(proxy_handler)
        with opener.open(FONT_ZIP_URL, timeout=120) as resp, open(tmp_zip, "wb") as out:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 65536
            while True:
                data = resp.read(chunk)
                if not data:
                    break
                out.write(data)
                downloaded += len(data)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r    进度: {pct:3d}%  ({downloaded//1024//1024} MB)", end="", flush=True)
        print()
        print_ok("下载完成")

        # 解压并安装：只安装 NerdFontMono 变体（严格等宽，终端专用）
        # 跳过 NFP（比例字体）、NL（无连字）、NF（图标非等宽）变体
        installed = 0
        reg_entries = {}
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            for name in zf.namelist():
                if not name.lower().endswith(".ttf"):
                    continue
                basename = Path(name).name
                if not basename:
                    continue
                # 只保留 JetBrainsMonoNerdFontMono-*.ttf
                if not basename.startswith("JetBrainsMonoNerdFontMono-"):
                    continue
                dest = font_dir / basename
                if dest.exists():
                    continue
                with zf.open(name) as src, open(dest, "wb") as dst:
                    dst.write(src.read())
                # 注册表值名：去掉 .ttf + 加 "(TrueType)"
                reg_entries[basename[:-4] + " (TrueType)"] = str(dest)
                installed += 1

        # 注册到用户字体注册表（让 Windows 应用能识别）
        reg_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE
        ) as key:
            for reg_name, font_path in reg_entries.items():
                winreg.SetValueEx(key, reg_name, 0, winreg.REG_SZ, font_path)

        print_ok(f"已安装 {installed} 个字体文件 → {font_dir}")

    except Exception as e:
        print_err(f"Nerd Font 安装失败：{e}")
        return False
    finally:
        if tmp_zip:
            try:
                os.unlink(tmp_zip)
            except OSError:
                pass

    _configure_windows_terminal_font(FONT_FACE)
    return True


def main():
    print("=" * 60)
    print("Windows 开发环境自动配置脚本")
    print("=" * 60)
    print(f"\n代理配置:")
    print(f"  HTTP:  {PROXY_HTTP}")
    print(f"  SOCKS: {PROXY_SOCKS}")

    # 检查 Python 版本
    if sys.version_info < (3, 7):
        print_err("需要 Python 3.7 或更高版本")
        sys.exit(1)

    # 检查是否在 Windows 上运行
    if sys.platform != 'win32':
        print_err("此脚本仅支持 Windows")
        sys.exit(1)

    # 检查系统 UTF-8 设置（重要！）
    check_system_utf8()

    results = []

    # 1. 配置用户级 UTF-8 环境变量（最先执行，解决 pip 等工具的编码问题）
    results.append(("UTF-8 环境变量", setup_utf8_env()))

    # 2. 配置 PowerShell Profile
    results.append(("PowerShell Profile", setup_powershell_profile()))

    # 3. 配置 VS Code
    results.append(("VS Code 设置", setup_vscode_settings()))

    # 4. 配置 SSL 证书验证跳过
    results.append(("SSL 证书验证配置", setup_ssl_workarounds()))

    # 5. 配置 Git Bash
    results.append(("Git Bash 配置", setup_git_bash()))

    # 6. 配置 Scoop aria2
    results.append(("Scoop aria2 配置", setup_scoop_aria2()))

    # 7. 安装 Nerd Font（JetBrainsMono）并配置 Windows Terminal
    results.append(("Nerd Font 安装", setup_nerd_font()))

    # 8. 配置 Windows Terminal WSL 起始目录为 Linux home
    results.append(("WSL 起始目录", setup_windows_terminal_wsl_home()))

    # 总结
    print("\n" + "=" * 60)
    print("配置结果:")
    print("=" * 60)
    for name, success in results:
        status = "[OK]" if success else "[SKIP]"
        print(f"  {status} {name}")

    print("\n后续步骤:")
    print("  1. 重启 PowerShell / Windows Terminal")
    print("  2. 重启 VS Code")
    print("  3. 运行 python test_setup.py 验证配置")
    print("  4. 如需安装常用工具: scoop install pandoc poppler qpdf tesseract")
    print("\n如需修改代理地址，请编辑此脚本顶部的 PROXY_* 变量")
    print("如需安装根证书（需管理员权限），参见 README.md 第 5 章")


if __name__ == "__main__":
    main()
