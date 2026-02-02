# Windows 开发环境配置 - 快速参考

## 🚀 快速安装

```powershell
# 1. 运行自动配置脚本
python setup.py

# 2. 重启 PowerShell / VS Code

# 3. 运行测试验证
python test_setup.py
```

---

## 📋 常用命令

### 代理管理

| 命令 | 说明 | 使用场景 |
|------|------|---------|
| `Lock-Proxy` | 🔒 锁定代理 | **推荐用于 Claude Code**<br>代理始终开启，不跟随系统设置 |
| `Unlock-Proxy` | 🔓 解锁代理 | 恢复自动检测模式 |
| `Get-ProxyStatus` | 查看代理状态 | 显示所有代理配置详情 |
| `proxy-status` | 查看代理状态（别名） | 同上 |
| `Sync-ProxyToTools` | 同步代理到工具 | 同步到 git/npm/scoop |
| `proxy-sync` | 同步代理（别名） | 同上 |

### 手动控制

| 命令 | 说明 |
|------|------|
| `Set-AutoProxy` | 重新检测代理状态 |
| `Enable-Proxy` | 强制开启代理（当前会话） |
| `Disable-Proxy` | 强制关闭代理（当前会话） |

---

## 🔒 代理锁定模式（推荐）

### 为什么需要锁定？

使用 Claude Code 等应用时可能遇到的问题：

| 场景 | 问题 | 解决 |
|------|------|------|
| 关闭系统代理后打开新终端 | Claude Code 无法连接 | 🔒 锁定代理 |
| 旧终端能用，新终端不能 | 环境变量不一致 | 🔒 锁定代理 |
| API 中转站直连慢且不稳定 | 网络路由问题 | 🔒 锁定代理 |

### 使用方法

```powershell
# 一次性设置，长期有效
Lock-Proxy

# 现在可以：
# ✅ 随时打开新终端
# ✅ 随时启动 Claude Code
# ✅ 无需关心系统代理开关
# ✅ 只需确保代理软件（Clash）在运行
```

### 工作原理

```
锁定前：
系统代理开关 ON  → 有 HTTP_PROXY → 应用使用代理
系统代理开关 OFF → 无 HTTP_PROXY → 应用直连（可能失败）

锁定后：
无论系统代理开关 → 始终有 HTTP_PROXY → 应用始终使用代理
```

---

## ⚙️ 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| PowerShell Profile | `~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1` | 代理自动检测和锁定逻辑 |
| VS Code 设置 | `%APPDATA%\Code\User\settings.json` | 终端、编码、Emoji 配置 |
| Git Bash 配置 | `~/.minttyrc` 和 `~/.bash_profile` | UTF-8 和 Emoji 支持 |
| 代理锁定文件 | `~/.proxy_lock` | 存在时表示已锁定 |

---

## 🔧 故障排查

### Claude Code 无法连接

**症状**：新终端启动 Claude Code 无法连接，但旧终端可以

**原因**：新终端没有代理环境变量

**解决**：
```powershell
# 方案 1：锁定代理（推荐）
Lock-Proxy
# 重新启动 Claude Code

# 方案 2：检查代理状态
Get-ProxyStatus
# 如果代理未设置，运行 Set-AutoProxy
```

---

### 代理软件关闭导致无法连接

**症状**：提示连接被拒绝或超时

**原因**：代理环境变量指向 `127.0.0.1:33210`，但代理软件未运行

**解决**：
```powershell
# 检查代理软件（Clash）是否在运行
netstat -ano | findstr "33210"

# 如果没有输出，启动代理软件

# 或者临时解锁代理
Unlock-Proxy
```

---

### 中文乱码

**症状**：PowerShell 或 Claude Code 输出中文乱码

**原因**：系统未启用 UTF-8 全局支持

**解决**：
```powershell
# 以管理员身份运行
.\enable_utf8_system.ps1

# 重启计算机
```

---

### VS Code 终端 Emoji 乱码

**症状**：VS Code 终端中 Emoji 显示为方框或乱码

**已修复**：运行 `python setup.py` 会自动配置以下设置：
- 使用 Cascadia Mono 字体
- Unicode 版本设为 11
- 启动时设置代码页 65001
- 关闭 GPU 加速

**如果仍有问题**：使用 Windows Terminal（Ctrl+Shift+C 打开外部终端）

---

## 📊 测试验证

```powershell
# 运行完整测试
python test_setup.py

# 关键测试项：
# ✅ PowerShell Profile 配置
# ✅ 代理锁定状态
# ✅ 系统 UTF-8 全局支持
# ✅ PowerShell -NoProfile 中文输出
```

---

## 💡 最佳实践

### 日常使用（推荐配置）

```powershell
# 1. 一次性锁定代理
Lock-Proxy

# 2. 保持代理软件（Clash）常驻运行
#    - 即使关闭系统代理开关也没关系
#    - 浏览器等系统应用会直连
#    - Claude Code 等会通过代理

# 3. 需要时查看状态
proxy-status
```

### 临时切换场景

```powershell
# 切换到直连模式
Unlock-Proxy          # 解锁代理
# 关闭系统代理开关
# 打开新终端（会自动检测为直连）

# 切换回代理模式
# 开启系统代理开关
# 打开新终端（会自动检测为代理）

# 或直接锁定
Lock-Proxy            # 锁定代理
```

---

## 📚 相关文档

- [README.md](README.md) - 完整配置指南
- [CLAUDE_PROXY_GUIDE.md](CLAUDE_PROXY_GUIDE.md) - Claude Code 代理问题详细说明
- [setup.py](setup.py) - 自动配置脚本
- [test_setup.py](test_setup.py) - 测试验证脚本

---

## 🆘 获取帮助

遇到问题？

1. 运行 `python test_setup.py` 查看哪里配置不正确
2. 运行 `Get-ProxyStatus` 查看代理状态
3. 查看 [README.md](README.md) 相关章节
4. 查看 GitHub Issues

---

**提示**：大多数问题都可以通过 `Lock-Proxy` 解决！ 🎉
