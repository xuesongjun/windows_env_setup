# 代理状态检查脚本
# 用于快速查看完整的代理配置状态

Write-Host "`n" -NoNewline
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       代理配置状态检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 代理锁定状态
Write-Host "`n[1] 代理锁定状态" -ForegroundColor Yellow
$lockFile = "$env:USERPROFILE\.proxy_lock"
if (Test-Path $lockFile) {
    Write-Host "    🔒 已锁定" -ForegroundColor Green
    Write-Host "       - 代理保持开启，不跟随系统设置" -ForegroundColor Gray
    Write-Host "       - 所有新终端都会自动使用代理" -ForegroundColor Gray
    Write-Host "       - 使用 'Unlock-Proxy' 解锁" -ForegroundColor Gray
} else {
    Write-Host "    🔓 未锁定 (自动检测模式)" -ForegroundColor Yellow
    Write-Host "       - 代理跟随 Windows 系统代理开关" -ForegroundColor Gray
    Write-Host "       - 使用 'Lock-Proxy' 锁定代理" -ForegroundColor Gray
}

# 2. Windows 系统代理设置
Write-Host "`n[2] Windows 系统代理开关" -ForegroundColor Yellow
try {
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    $proxyEnable = (Get-ItemProperty -Path $regPath -Name ProxyEnable -ErrorAction SilentlyContinue).ProxyEnable
    $proxyServer = (Get-ItemProperty -Path $regPath -Name ProxyServer -ErrorAction SilentlyContinue).ProxyServer

    if ($proxyEnable -eq 1) {
        Write-Host "    ✓ 已开启" -ForegroundColor Green
        if ($proxyServer) {
            Write-Host "       服务器: $proxyServer" -ForegroundColor Gray
        }
    } else {
        Write-Host "    ✗ 已关闭" -ForegroundColor Yellow
        if ($proxyServer) {
            Write-Host "       配置的服务器: $proxyServer (未启用)" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "    ⚠ 无法读取" -ForegroundColor Red
}

# 3. 用户级环境变量（新进程会读取）
Write-Host "`n[3] 用户级环境变量 (对新进程生效)" -ForegroundColor Yellow
$userHttpProxy = [Environment]::GetEnvironmentVariable("HTTP_PROXY", "User")
$userHttpsProxy = [Environment]::GetEnvironmentVariable("HTTPS_PROXY", "User")
$userAllProxy = [Environment]::GetEnvironmentVariable("ALL_PROXY", "User")

if ($userHttpProxy) {
    Write-Host "    ✓ 已设置" -ForegroundColor Green
    Write-Host "       HTTP_PROXY  = $userHttpProxy" -ForegroundColor Gray
    Write-Host "       HTTPS_PROXY = $userHttpsProxy" -ForegroundColor Gray
    Write-Host "       ALL_PROXY   = $userAllProxy" -ForegroundColor Gray
} else {
    Write-Host "    ✗ 未设置" -ForegroundColor Yellow
}

# 4. 当前会话环境变量
Write-Host "`n[4] 当前会话环境变量" -ForegroundColor Yellow
if ($env:HTTP_PROXY) {
    Write-Host "    ✓ 已设置" -ForegroundColor Green
    Write-Host "       HTTP_PROXY  = $env:HTTP_PROXY" -ForegroundColor Gray
    Write-Host "       HTTPS_PROXY = $env:HTTPS_PROXY" -ForegroundColor Gray
    Write-Host "       ALL_PROXY   = $env:ALL_PROXY" -ForegroundColor Gray
} else {
    Write-Host "    ✗ 未设置" -ForegroundColor Yellow
}

# 5. 代理端口监听状态
Write-Host "`n[5] 代理软件运行状态" -ForegroundColor Yellow
$proxyPort = "33210"
$listening = netstat -ano | Select-String "LISTENING" | Select-String $proxyPort

if ($listening) {
    Write-Host "    ✓ 代理端口 $proxyPort 正在监听" -ForegroundColor Green
    # 取第一行匹配，避免多行时解析错误
    $firstMatch = $listening | Select-Object -First 1
    $processId = ("$firstMatch" -split "\s+")[-1]
    try {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "       进程: $($process.Name) (PID: $processId)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "       进程 ID: $processId" -ForegroundColor Gray
    }
} else {
    Write-Host "    ✗ 代理端口 $proxyPort 未监听" -ForegroundColor Red
    Write-Host "       ⚠ 代理软件可能未运行" -ForegroundColor Yellow
}

# 6. Git 配置
Write-Host "`n[6] Git 代理配置" -ForegroundColor Yellow
$gitProxy = git config --global --get http.proxy 2>$null
if ($gitProxy) {
    Write-Host "    ✓ 已配置" -ForegroundColor Green
    Write-Host "       http.proxy = $gitProxy" -ForegroundColor Gray
} else {
    Write-Host "    ✗ 未配置" -ForegroundColor Yellow
}

# 7. npm 配置
Write-Host "`n[7] npm 代理配置" -ForegroundColor Yellow
try {
    $npmProxy = npm config get proxy 2>$null
    if ($npmProxy -and $npmProxy -ne "null") {
        Write-Host "    ✓ 已配置" -ForegroundColor Green
        Write-Host "       proxy = $npmProxy" -ForegroundColor Gray
    } else {
        Write-Host "    ✗ 未配置" -ForegroundColor Yellow
    }
} catch {
    Write-Host "    ⚠ npm 未安装" -ForegroundColor Yellow
}

# 总结建议
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "       状态总结与建议" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$lockExists = Test-Path $lockFile
$proxyRunning = $null -ne $listening
$sessionProxySet = $null -ne $env:HTTP_PROXY
$userProxySet = $null -ne $userHttpProxy

Write-Host ""
if ($lockExists -and $proxyRunning) {
    Write-Host "✅ 配置正常：代理已锁定，代理软件正在运行" -ForegroundColor Green
    Write-Host "   Claude Code 应该可以正常使用" -ForegroundColor Green
} elseif ($lockExists -and -not $proxyRunning) {
    Write-Host "⚠️ 警告：代理已锁定，但代理软件未运行" -ForegroundColor Yellow
    Write-Host "   请启动代理软件 (Clash/V2Ray)" -ForegroundColor Yellow
} elseif (-not $lockExists -and $proxyRunning -and $sessionProxySet) {
    Write-Host "✅ 配置正常：自动检测模式，当前会话使用代理" -ForegroundColor Green
} elseif (-not $lockExists -and -not $sessionProxySet) {
    Write-Host "ℹ️ 信息：当前会话未使用代理" -ForegroundColor Cyan
    if ($proxyRunning) {
        Write-Host "   代理软件正在运行，但环境变量未设置" -ForegroundColor Cyan
        Write-Host "   建议：运行 'Lock-Proxy' 锁定代理（推荐用于 Claude Code）" -ForegroundColor Cyan
    } else {
        Write-Host "   代理软件未运行" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
