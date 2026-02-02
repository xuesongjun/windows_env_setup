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

# 设置用户级环境变量（永久生效）
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
[Environment]::SetEnvironmentVariable("PYTHONIOENCODING", "utf-8", "User")

# ========== 智能代理配置 ==========
$PROXY_HTTP = "{proxy_http}"
$PROXY_SOCKS = "{proxy_socks}"
$PROXY_HOST_PORT = "{proxy_host_port}"

# 自动检测并设置代理（检测 Windows 代理设置开关）
function Set-AutoProxy {{
    $regPath = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings"
    $proxyEnable = (Get-ItemProperty -Path $regPath -Name ProxyEnable -ErrorAction SilentlyContinue).ProxyEnable

    if ($proxyEnable -eq 1) {{
        $env:HTTP_PROXY = $PROXY_HTTP
        $env:HTTPS_PROXY = $PROXY_HTTP
        $env:ALL_PROXY = $PROXY_SOCKS
        [System.Environment]::SetEnvironmentVariable("HTTP_PROXY", $PROXY_HTTP, "User")
        [System.Environment]::SetEnvironmentVariable("HTTPS_PROXY", $PROXY_HTTP, "User")
        [System.Environment]::SetEnvironmentVariable("ALL_PROXY", $PROXY_SOCKS, "User")
        git config --global http.proxy $PROXY_HTTP 2>$null
        git config --global https.proxy $PROXY_HTTP 2>$null
        scoop config proxy $PROXY_HOST_PORT 2>$null
        npm config set proxy $PROXY_HTTP 2>$null
        npm config set https-proxy $PROXY_HTTP 2>$null
        Write-Host "[Proxy] Enabled: $PROXY_HTTP (env/git/scoop/npm + system)" -ForegroundColor Green
    }} else {{
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
        Write-Host "[Proxy] Direct connection (all cleared)" -ForegroundColor Yellow
    }}
}}

# 手动开启代理
function Enable-Proxy {{
    $env:HTTP_PROXY = $PROXY_HTTP
    $env:HTTPS_PROXY = $PROXY_HTTP
    $env:ALL_PROXY = $PROXY_SOCKS
    [System.Environment]::SetEnvironmentVariable("HTTP_PROXY", $PROXY_HTTP, "User")
    [System.Environment]::SetEnvironmentVariable("HTTPS_PROXY", $PROXY_HTTP, "User")
    [System.Environment]::SetEnvironmentVariable("ALL_PROXY", $PROXY_SOCKS, "User")
    git config --global http.proxy $PROXY_HTTP 2>$null
    git config --global https.proxy $PROXY_HTTP 2>$null
    scoop config proxy $PROXY_HOST_PORT 2>$null
    npm config set proxy $PROXY_HTTP 2>$null
    npm config set https-proxy $PROXY_HTTP 2>$null
    Write-Host "[Proxy] Manually enabled (all + system)" -ForegroundColor Green
}}

# 手动关闭代理
function Disable-Proxy {{
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
    Write-Host "[Proxy] Disabled (all cleared)" -ForegroundColor Yellow
}}

# 查看代理状态
function Get-ProxyStatus {{
    if ($env:HTTP_PROXY) {{
        Write-Host "[Proxy] Current: $env:HTTP_PROXY" -ForegroundColor Green
    }} else {{
        Write-Host "[Proxy] Current: Direct (no proxy)" -ForegroundColor Yellow
    }}
}}

# 启动时自动检测
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
    except:
        pass

    return None


def setup_powershell_profile():
    """配置 PowerShell 7 profile"""
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

    # 检查是否已存在
    if ps_profile_path.exists():
        existing_content = ps_profile_path.read_text(encoding='utf-8')
        if "智能代理配置" in existing_content:
            print_warn(f"Profile 已包含代理配置，跳过: {ps_profile_path}")
            return True

        # 备份现有文件
        backup_path = ps_profile_path.with_suffix('.ps1.bak')
        ps_profile_path.rename(backup_path)
        print_ok(f"已备份现有 profile: {backup_path}")

        # 合并内容
        profile_content = existing_content + "\n\n" + profile_content

    # 写入文件
    ps_profile_path.write_text(profile_content, encoding='utf-8')
    print_ok(f"已创建/更新 profile: {ps_profile_path}")

    # 同时配置 Windows PowerShell 5.x（可选）
    ps5_profile_dir = Path.home() / "Documents" / "WindowsPowerShell"
    ps5_profile_path = ps5_profile_dir / "Microsoft.PowerShell_profile.ps1"

    if not ps5_profile_path.exists():
        ps5_profile_dir.mkdir(parents=True, exist_ok=True)
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
                "path": pwsh_path.replace("\\", "\\\\"),
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

    # 合并设置
    settings.update(new_settings)

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

    # 1. 创建 ~/.curlrc
    curlrc_path = Path.home() / ".curlrc"
    try:
        curlrc_content = "# 跳过 SSL 证书验证（解决缺少根证书问题）\ninsecure\n"
        curlrc_path.write_text(curlrc_content, encoding='utf-8')
        print_ok(f"已创建 ~/.curlrc (curl 跳过证书验证)")
        results.append(True)
    except Exception as e:
        print_err(f"创建 ~/.curlrc 失败: {e}")
        results.append(False)

    # 2. 配置 Git 跳过 SSL 验证
    try:
        result = subprocess.run(
            ["git", "config", "--global", "http.sslVerify", "false"],
            capture_output=True, text=True, shell=True
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
    配置 Git Bash 的 UTF-8 和 Emoji 支持

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
        minttyrc_path.write_text(minttyrc_content, encoding='utf-8')
        print_ok(f"已创建 ~/.minttyrc (Git Bash 终端配置)")
        results.append(True)
    except Exception as e:
        print_err(f"创建 ~/.minttyrc 失败: {e}")
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


def setup_claude_skills():
    """配置 Claude Code Skills 目录"""
    print_step("配置 Claude Code Skills...")

    skills_dir = Path.home() / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # 示例 skills
    example_skills = {
        "code-review": {
            "name": "code-review",
            "description": "对代码文件进行质量、安全性和性能审查",
            "content": """# 代码审查

请对指定的代码文件进行审查，检查以下方面：

## 审查项目

1. **代码质量** - 命名、函数长度、重复代码
2. **潜在 Bug** - 空指针、边界条件、错误处理
3. **安全性** - 输入验证、注入风险
4. **性能** - 明显的性能问题

请提供具体的改进建议和代码示例。

目标：$ARGUMENTS"""
        },
        "explain": {
            "name": "explain",
            "description": "详细解释指定的代码，包括功能、流程和使用方法",
            "content": """# 代码解释

请详细解释指定的代码，包括：

1. **整体功能**：代码的主要目的
2. **工作流程**：执行流程
3. **关键部分**：重点解释复杂代码段
4. **依赖关系**：外部依赖或内部模块
5. **使用示例**：如何使用

请用通俗易懂的语言解释。

目标：$ARGUMENTS"""
        },
        "git-summary": {
            "name": "git-summary",
            "description": "显示当前 Git 仓库的状态摘要",
            "content": """# Git 仓库状态摘要

请执行以下操作：

1. 显示当前分支名称
2. 显示最近 5 条提交记录
3. 显示未提交的更改
4. 显示未跟踪的文件
5. 显示与远程的同步状态

$ARGUMENTS"""
        }
    }

    for skill_name, skill_data in example_skills.items():
        skill_dir = skills_dir / skill_name
        skill_dir.mkdir(exist_ok=True)

        skill_md = skill_dir / "SKILL.md"
        content = f"""---
name: {skill_data['name']}
description: {skill_data['description']}
---

{skill_data['content']}
"""
        skill_md.write_text(content, encoding='utf-8')
        print_ok(f"已创建 skill: {skill_name}")

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

    results = []

    # 1. 配置 PowerShell Profile
    results.append(("PowerShell Profile", setup_powershell_profile()))

    # 2. 配置 VS Code
    results.append(("VS Code 设置", setup_vscode_settings()))

    # 3. 配置 SSL 证书验证跳过
    results.append(("SSL 证书验证配置", setup_ssl_workarounds()))

    # 4. 配置 Git Bash
    results.append(("Git Bash 配置", setup_git_bash()))

    # 5. 配置 Claude Skills
    results.append(("Claude Skills", setup_claude_skills()))

    # 6. 配置 Scoop aria2
    results.append(("Scoop aria2 配置", setup_scoop_aria2()))

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
