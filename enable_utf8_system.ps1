# 启用 Windows Beta UTF-8 支持
# 此脚本需要管理员权限运行

Write-Host "正在检查管理员权限..." -ForegroundColor Cyan

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "错误：需要管理员权限！" -ForegroundColor Red
    Write-Host "请右键点击 PowerShell 并选择 '以管理员身份运行'，然后重新执行此脚本。" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ 已确认管理员权限" -ForegroundColor Green
Write-Host ""

# 检查当前设置
$currentValue = (Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Nls\CodePage" -Name "ACP" -ErrorAction SilentlyContinue).ACP

Write-Host "当前系统代码页设置："
if ($currentValue -eq "65001") {
    Write-Host "  已启用 UTF-8 (65001)" -ForegroundColor Green
    Write-Host ""
    Write-Host "系统已经配置为 UTF-8，无需更改。"
    exit 0
} else {
    Write-Host "  当前代码页: $currentValue (GBK/系统默认)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "将要执行的操作：" -ForegroundColor Cyan
Write-Host "  1. 启用 Beta UTF-8 全局支持"
Write-Host "  2. 设置系统代码页为 65001 (UTF-8)"
Write-Host "  3. 重启后生效"
Write-Host ""
Write-Host "影响范围：" -ForegroundColor Yellow
Write-Host "  ✓ 所有新启动的程序将默认使用 UTF-8"
Write-Host "  ✓ PowerShell、CMD、Python 等都会默认输出 UTF-8"
Write-Host "  ⚠ 需要重启计算机才能生效"
Write-Host "  ⚠ 可能影响老旧的不支持 UTF-8 的程序（极少见）"
Write-Host ""

$confirm = Read-Host "是否继续？(Y/N)"
if ($confirm -ne 'Y' -and $confirm -ne 'y') {
    Write-Host "操作已取消。" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "正在配置..." -ForegroundColor Cyan

try {
    # 启用 Beta UTF-8 支持
    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Nls\CodePage" -Name "ACP" -Value "65001"
    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Nls\CodePage" -Name "OEMCP" -Value "65001"

    Write-Host "✓ 配置完成！" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步：" -ForegroundColor Cyan
    Write-Host "  1. 重启计算机"
    Write-Host "  2. 重启后，所有程序将默认使用 UTF-8"
    Write-Host "  3. Claude 的输出将不再乱码"
    Write-Host ""
    Write-Host "如需还原，以管理员身份运行：" -ForegroundColor Gray
    Write-Host "  Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Nls\CodePage' -Name 'ACP' -Value '936'"
    Write-Host "  Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Nls\CodePage' -Name 'OEMCP' -Value '936'"
    Write-Host ""

    $restart = Read-Host "是否立即重启计算机？(Y/N)"
    if ($restart -eq 'Y' -or $restart -eq 'y') {
        Write-Host "正在重启..." -ForegroundColor Yellow
        Restart-Computer -Force
    } else {
        Write-Host "请记得稍后重启计算机以使更改生效。" -ForegroundColor Yellow
    }

} catch {
    Write-Host "错误：$_" -ForegroundColor Red
    exit 1
}
