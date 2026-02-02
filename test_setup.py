# -*- coding: utf-8 -*-
"""
Windows 开发环境配置测试脚本
验证 PowerShell、VS Code、代理、编码等配置是否正确

使用方法: python test_setup.py
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


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(msg):
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")


def print_test(name):
    print(f"\n[TEST] {name}")


def print_pass(msg):
    print(f"  {Colors.GREEN}[PASS]{Colors.RESET} {msg}")


def print_fail(msg):
    print(f"  {Colors.RED}[FAIL]{Colors.RESET} {msg}")


def print_warn(msg):
    print(f"  {Colors.YELLOW}[WARN]{Colors.RESET} {msg}")


def print_info(msg):
    print(f"  [INFO] {msg}")


def test_python_encoding():
    """测试 Python 编码配置"""
    print_test("Python 编码配置")

    results = []

    # stdout 编码
    stdout_enc = sys.stdout.encoding.lower()
    if 'utf' in stdout_enc:
        print_pass(f"stdout 编码: {stdout_enc}")
        results.append(True)
    else:
        print_fail(f"stdout 编码: {stdout_enc} (应为 utf-8)")
        results.append(False)

    # PYTHONIOENCODING 环境变量
    pythonio = os.environ.get('PYTHONIOENCODING', '')
    if pythonio.lower() == 'utf-8':
        print_pass(f"PYTHONIOENCODING: {pythonio}")
        results.append(True)
    else:
        print_warn(f"PYTHONIOENCODING: {pythonio or '(未设置)'}")
        results.append(True)  # 不是致命问题

    # 测试中文输出
    try:
        test_str = "中文测试 Chinese Test"
        print_pass(f"中文输出测试: {test_str}")
        results.append(True)
    except Exception as e:
        print_fail(f"中文输出失败: {e}")
        results.append(False)

    return all(results)


def test_powershell_7():
    """测试 PowerShell 7 安装"""
    print_test("PowerShell 7 安装")

    try:
        result = subprocess.run(
            ["pwsh", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print_pass(f"PowerShell 版本: {version}")
            return True
        else:
            print_fail(f"PowerShell 执行失败: {result.stderr}")
            return False
    except FileNotFoundError:
        print_fail("PowerShell 7 (pwsh) 未安装")
        return False
    except Exception as e:
        print_fail(f"测试失败: {e}")
        return False


def test_powershell_profile():
    """测试 PowerShell Profile 配置"""
    print_test("PowerShell Profile 配置")

    profile_path = Path.home() / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"

    if not profile_path.exists():
        print_fail(f"Profile 不存在: {profile_path}")
        return False

    print_pass(f"Profile 存在: {profile_path}")

    content = profile_path.read_text(encoding='utf-8')

    checks = [
        ("UTF-8 编码设置", "UTF8" in content or "utf-8" in content.lower()),
        ("代理配置函数", "Set-AutoProxy" in content),
        ("chcp 65001", "65001" in content),
    ]

    results = []
    for name, passed in checks:
        if passed:
            print_pass(name)
            results.append(True)
        else:
            print_warn(f"{name} (未找到)")
            results.append(False)

    return all(results)


def test_vscode_settings():
    """测试 VS Code 设置"""
    print_test("VS Code 设置")

    settings_path = Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "settings.json"

    if not settings_path.exists():
        print_warn(f"VS Code 设置不存在: {settings_path}")
        return True  # VS Code 可能未安装

    print_pass(f"设置文件存在: {settings_path}")

    try:
        content = settings_path.read_text(encoding='utf-8')
        if content.startswith('\ufeff'):
            content = content[1:]
        settings = json.loads(content)
    except Exception as e:
        print_fail(f"读取设置失败: {e}")
        return False

    checks = [
        ("PowerShell 7 为默认终端", settings.get("terminal.integrated.defaultProfile.windows") == "PowerShell 7"),
        ("终端 UTF-8 环境变量", "LANG" in settings.get("terminal.integrated.env.windows", {})),
        ("文件编码 UTF-8", settings.get("files.encoding") == "utf8"),
    ]

    results = []
    for name, passed in checks:
        if passed:
            print_pass(name)
            results.append(True)
        else:
            print_warn(f"{name} (未配置)")
            results.append(False)

    return len([r for r in results if r]) >= 2  # 至少 2 项通过


def test_windows_proxy_setting():
    """测试 Windows 代理设置检测"""
    print_test("Windows 代理设置检测")

    try:
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            print_pass(f"ProxyEnable 值: {proxy_enable}")

            if proxy_enable:
                try:
                    proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                    print_info(f"代理服务器: {proxy_server}")
                except:
                    pass

            return True
    except Exception as e:
        print_fail(f"读取代理设置失败: {e}")
        return False


def test_environment_variables():
    """测试环境变量"""
    print_test("代理环境变量")

    vars_to_check = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]
    results = []

    for var in vars_to_check:
        value = os.environ.get(var, "")
        if value:
            print_pass(f"{var}: {value}")
        else:
            print_info(f"{var}: (未设置)")
        results.append(True)  # 环境变量是否设置取决于代理状态

    return True


def test_git_config():
    """测试 Git 配置"""
    print_test("Git 代理配置")

    try:
        result = subprocess.run(
            ["git", "config", "--global", "--get", "http.proxy"],
            capture_output=True,
            text=True
        )
        proxy = result.stdout.strip()
        if proxy:
            print_pass(f"Git http.proxy: {proxy}")
        else:
            print_info("Git http.proxy: (未设置)")

        return True
    except FileNotFoundError:
        print_warn("Git 未安装")
        return True
    except Exception as e:
        print_fail(f"测试失败: {e}")
        return False


def test_claude_skills():
    """测试 Claude Skills 配置"""
    print_test("Claude Skills 配置")

    skills_dir = Path.home() / ".claude" / "skills"

    if not skills_dir.exists():
        print_warn(f"Skills 目录不存在: {skills_dir}")
        return True

    skills = list(skills_dir.iterdir())
    if skills:
        print_pass(f"Skills 目录存在，包含 {len(skills)} 个 skill")
        for skill in skills[:5]:  # 只显示前 5 个
            skill_md = skill / "SKILL.md"
            if skill_md.exists():
                print_info(f"  - {skill.name}")
        return True
    else:
        print_warn("Skills 目录为空")
        return True


def test_console_codepage():
    """测试控制台代码页"""
    print_test("控制台代码页")

    try:
        result = subprocess.run(
            ["cmd", "/c", "chcp"],
            capture_output=True,
            text=True
        )
        output = result.stdout.strip()
        if "65001" in output:
            print_pass(f"代码页: 65001 (UTF-8)")
            return True
        else:
            print_warn(f"代码页: {output}")
            print_info("建议在 PowerShell 中运行 chcp 65001")
            return True
    except Exception as e:
        print_warn(f"无法检测代码页: {e}")
        return True


def test_scoop_aria2():
    """
    测试 Scoop aria2 配置

    aria2 是一个多协议下载工具，用于解决 Scoop 通过代理下载时的 SSL 证书问题。
    当使用 Clash 等代理（启用 HTTPS 解密）时，.NET 的 Invoke-WebRequest 会
    因为不信任代理证书而报错，而 aria2 可以配置跳过证书验证。
    """
    print_test("Scoop aria2 配置")

    try:
        # 检查 scoop 是否安装（使用 shell=True 因为 scoop 是 .cmd/.ps1 脚本）
        result = subprocess.run(
            ["scoop", "--version"],
            capture_output=True,
            text=True,
            shell=True,
            timeout=10
        )
        if result.returncode != 0:
            print_info("Scoop 未安装，跳过此测试")
            return None  # 返回 None 表示跳过
    except FileNotFoundError:
        print_info("Scoop 未安装，跳过此测试")
        return None
    except Exception as e:
        print_warn(f"无法检测 Scoop: {e}")
        return None

    print_pass("Scoop 已安装")

    # 检查 aria2 是否安装
    result = subprocess.run(
        ["scoop", "list"],
        capture_output=True,
        text=True,
        shell=True
    )
    if "aria2" in result.stdout:
        print_pass("aria2 已安装")
    else:
        print_fail("aria2 未安装（建议安装以解决 SSL 问题）")
        print_info("运行: scoop install aria2")
        return False

    # 检查 aria2 配置
    result = subprocess.run(
        ["scoop", "config"],
        capture_output=True,
        text=True,
        shell=True
    )
    config_output = result.stdout

    checks = [
        ("aria2-enabled = True", "aria2-enabled" in config_output and "True" in config_output),
        ("aria2-options 包含 --check-certificate=false", "check-certificate=false" in config_output),
    ]

    results = []
    for name, passed in checks:
        if passed:
            print_pass(name)
            results.append(True)
        else:
            print_fail(f"{name} (未配置)")
            results.append(False)

    if not all(results):
        print_info("建议运行以下命令配置 aria2:")
        print_info("  scoop config aria2-enabled true")
        print_info("  scoop config aria2-options '--check-certificate=false'")

    return all(results)


def test_ssl_mitm():
    """
    测试 SSL 证书验证配置

    检测系统是否已配置跳过 SSL 证书验证的解决方案。
    由于系统缺少 USERTrust ECC 根证书且无管理员权限安装，
    需要为各工具单独配置跳过证书验证。
    """
    print_test("SSL 证书验证配置")

    results = []

    # 检查 .curlrc 配置
    curlrc_path = Path.home() / ".curlrc"
    if curlrc_path.exists():
        content = curlrc_path.read_text(encoding='utf-8', errors='ignore')
        if 'insecure' in content:
            print_pass("curl 已配置 (~/.curlrc 含 'insecure')")
            results.append(True)
        else:
            print_fail("curl 配置不完整 (~/.curlrc 缺少 'insecure')")
            results.append(False)
    else:
        print_fail("curl 未配置 (~/.curlrc 不存在)")
        print_info("  运行: echo 'insecure' > ~/.curlrc")
        results.append(False)

    # 检查 Git SSL 配置
    try:
        result = subprocess.run(
            ["git", "config", "--global", "--get", "http.sslVerify"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip().lower() == 'false':
            print_pass("Git 已配置 (http.sslVerify = false)")
            results.append(True)
        else:
            print_fail("Git 未配置跳过 SSL 验证")
            print_info("  运行: git config --global http.sslVerify false")
            results.append(False)
    except FileNotFoundError:
        print_info("Git 未安装，跳过")
    except Exception as e:
        print_warn(f"Git 检测失败: {e}")

    # 检查 npm SSL 配置
    try:
        result = subprocess.run(
            ["npm", "config", "get", "strict-ssl"],
            capture_output=True,
            text=True,
            shell=True,
            timeout=10
        )
        if result.stdout.strip().lower() == 'false':
            print_pass("npm 已配置 (strict-ssl = false)")
            results.append(True)
        else:
            print_warn("npm 未配置跳过 SSL 验证")
            print_info("  运行: npm config set strict-ssl false")
    except FileNotFoundError:
        print_info("npm 未安装，跳过")
    except Exception:
        pass

    # 检查 Node.js 环境变量
    if os.environ.get('NODE_TLS_REJECT_UNAUTHORIZED') == '0':
        print_pass("Node.js 已配置 (NODE_TLS_REJECT_UNAUTHORIZED=0)")
    else:
        print_info("Node.js 环境变量未设置（在 PowerShell profile 中配置）")

    # 判断是否通过（至少 curl 和 Git 配置正确）
    if len(results) >= 2 and all(results[:2]):
        return True
    elif len(results) >= 1 and results[0]:
        return True
    else:
        return False


def test_emoji_output():
    """测试 emoji 输出（可能失败，取决于终端）"""
    print_test("Emoji 输出测试")

    try:
        # ASCII 替代文字（总是能正常显示）
        print_info("ASCII 替代: [rocket] [check] [cross] [party]")

        # 真实 emoji 测试
        emojis = "\U0001F680 \u2705 \u274C \U0001F389"  # 🚀 ✅ ❌ 🎉
        print_info(f"Emoji 测试: {emojis}")
        print_info("如果上面显示乱码，说明终端不支持 emoji（VS Code 已知问题）")
        print_info("在 Windows Terminal 中运行此脚本可正常显示")
        return True
    except Exception as e:
        print_warn(f"Emoji 测试失败: {e}")
        return True


def main():
    print_header("Windows 开发环境配置测试")

    tests = [
        ("Python 编码", test_python_encoding),
        ("PowerShell 7", test_powershell_7),
        ("PowerShell Profile", test_powershell_profile),
        ("VS Code 设置", test_vscode_settings),
        ("Windows 代理设置", test_windows_proxy_setting),
        ("环境变量", test_environment_variables),
        ("Git 配置", test_git_config),
        ("Scoop aria2", test_scoop_aria2),
        ("SSL 证书配置", test_ssl_mitm),
        ("Claude Skills", test_claude_skills),
        ("控制台代码页", test_console_codepage),
        ("Emoji 输出", test_emoji_output),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print_fail(f"测试异常: {e}")
            results.append((name, False))

    # 总结
    print_header("测试结果总结")

    passed_count = 0
    failed_count = 0
    skipped_count = 0

    for name, passed in results:
        if passed is None:
            status = f"{Colors.YELLOW}SKIP{Colors.RESET}"
            skipped_count += 1
        elif passed:
            status = f"{Colors.GREEN}PASS{Colors.RESET}"
            passed_count += 1
        else:
            status = f"{Colors.RED}FAIL{Colors.RESET}"
            failed_count += 1
        print(f"  [{status}] {name}")

    total_count = len(results)
    print(f"\n总计: {passed_count} 通过, {failed_count} 失败, {skipped_count} 跳过 (共 {total_count} 项)")

    if failed_count == 0:
        print(f"\n{Colors.GREEN}所有测试通过！{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}有 {failed_count} 项测试未通过，请检查上述输出。{Colors.RESET}")


if __name__ == "__main__":
    main()
