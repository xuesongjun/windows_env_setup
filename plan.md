# setup.py 改动计划

## 目标
1. 修复 `Update-Env` 花括号转义 Bug
2. 代理端口动态从 Windows 注册表读取（方案 A）
3. 优化 `Set-AutoProxy` 用户级环境变量写入（只在变化时写注册表）
4. 删除 `setup_claude_skills()` 死代码

---

## 改动一：修复 `Update-Env` 花括号转义（Bug）

**位置**：`POWERSHELL_PROFILE` 模板内，约第 249-252 行

**问题**：`function Update-Env {` 和 `}` 使用单括号，在 Python `.format()` 调用时会抛 `KeyError`

**改法**：
```python
# 改前
function Update-Env {
    ...
}

# 改后
function Update-Env {{
    ...
}}
```

---

## 改动二：代理地址动态从注册表读取

**位置**：`POWERSHELL_PROFILE` 模板

### 2a. 顶部变量改为兜底默认值

```powershell
# 改前（运行时固定值）
$PROXY_HTTP = "{proxy_http}"
$PROXY_SOCKS = "{proxy_socks}"
$PROXY_HOST_PORT = "{proxy_host_port}"

# 改后（只作为注册表读不到时的兜底）
$PROXY_FALLBACK_HTTP = "{proxy_http}"
$PROXY_FALLBACK_SOCKS = "{proxy_socks}"
$PROXY_FALLBACK_HOST_PORT = "{proxy_host_port}"
```

### 2b. 新增 `Get-SystemProxyAddress` 辅助函数

读取 Windows 系统代理注册表中的 `ProxyServer` 字段（格式如 `127.0.0.1:7897`），
**不管 ProxyEnable 状态**（Enable-Proxy 在系统代理关闭时也需要能用）。

```powershell
function Get-SystemProxyAddress {{
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    $props = Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue
    if ($props.ProxyServer) {{ return $props.ProxyServer }}
    return $null
}}
```

### 2c. 重构 `Set-AutoProxy`

- 读 `ProxyEnable` + `ProxyServer`，动态构建 HTTP/SOCKS5 URL
- 用户级环境变量写入前先比较旧值，**只在变化时才写注册表**（解决启动慢问题）
- HTTP 和 SOCKS5 使用同一端口（现代客户端如 Clash Verge Rev 使用混合端口）

```powershell
function Set-AutoProxy {{
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    $props   = Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue
    $proxyEnable = $props.ProxyEnable
    $proxyServer = $props.ProxyServer   # 如 "127.0.0.1:7897"

    if ($proxyEnable -eq 1 -and $proxyServer) {{
        $httpProxy  = "http://$proxyServer"
        $socksProxy = "socks5://$proxyServer"

        $env:HTTP_PROXY  = $httpProxy
        $env:HTTPS_PROXY = $httpProxy
        $env:ALL_PROXY   = $socksProxy

        # 只在值变化时写注册表（避免每次启动都写，节省约 150-300ms）
        $currentHttp = [Environment]::GetEnvironmentVariable("HTTP_PROXY", "User")
        if ($currentHttp -ne $httpProxy) {{
            [Environment]::SetEnvironmentVariable("HTTP_PROXY",  $httpProxy,  "User")
            [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $httpProxy,  "User")
            [Environment]::SetEnvironmentVariable("ALL_PROXY",   $socksProxy, "User")
        }}
        Write-Host "[Proxy] $httpProxy" -ForegroundColor Green
    }} else {{
        $env:HTTP_PROXY  = $null
        $env:HTTPS_PROXY = $null
        $env:ALL_PROXY   = $null

        $currentHttp = [Environment]::GetEnvironmentVariable("HTTP_PROXY", "User")
        if ($currentHttp) {{
            [Environment]::SetEnvironmentVariable("HTTP_PROXY",  $null, "User")
            [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $null, "User")
            [Environment]::SetEnvironmentVariable("ALL_PROXY",   $null, "User")
        }}
        Write-Host "[Proxy] Direct connection" -ForegroundColor Yellow
    }}
}}
```

### 2d. 更新 `Enable-Proxy` 和 `Lock-Proxy`

两个函数都改为：先调 `Get-SystemProxyAddress`，读不到时才用兜底常量。

```powershell
function Enable-Proxy {{
    $proxyServer = Get-SystemProxyAddress
    if (-not $proxyServer) {{ $proxyServer = $PROXY_FALLBACK_HOST_PORT }}
    $httpProxy  = "http://$proxyServer"
    $socksProxy = "socks5://$proxyServer"
    $env:HTTP_PROXY  = $httpProxy
    $env:HTTPS_PROXY = $httpProxy
    $env:ALL_PROXY   = $socksProxy
    Write-Host "[Proxy] Enabled: $httpProxy (session)" -ForegroundColor Green
    $response = Read-Host "Sync to git/npm/scoop? (Y/n)"
    if ($response -ne 'n' -and $response -ne 'N') {{ Sync-ProxyToTools }}
}}

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
```

---

## 改动三：删除死代码

- 删除 `setup_claude_skills()` 函数（约 808-888 行）
- 删除 `main()` 中对应的注释行（约 929-930 行）

---

## 不改动的部分

- `setup_utf8_env()`：已经有变化检测，逻辑正确
- `setup_vscode_settings()`、`setup_ssl_workarounds()`、`setup_git_bash()`：无问题
- `setup_scoop_aria2()`：轻微优化留到以后
- `setup.py` 顶部常量 `PROXY_HTTP` 等：保留作兜底默认值，加注释说明

---

## 影响评估

- **需要重新运行 `setup.py`** 才能更新已有 profile
- `check_proxy.ps1` 和 `test_setup.py` 的硬编码端口问题本次**不改**（非 setup.py 范围）
- 换了 VPN 客户端后，只需重启 Windows Terminal（profile 重新执行），无需重跑 `setup.py`
