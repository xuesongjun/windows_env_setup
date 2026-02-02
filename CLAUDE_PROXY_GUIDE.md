# Claude Code 代理连接问题解决方案

## 问题总结

**问题根源**：
1. 在中国大陆，直连 Anthropic API 会被阻断（403 Forbidden）
2. 必须使用代理才能连接 Claude Code
3. 旧的终端会话会保留启动时的环境变量，即使后来关闭代理也不会更新

**具体症状**：
- 断开代理后，新终端启动 Claude Code 无法连接（因为没有代理）
- 旧终端（代理开启时打开的）即使代理关闭也能用（因为环境变量未更新）

## 解决方案

### 方案 1：使用代理锁定模式（推荐）

如果您经常使用 Claude Code，建议**锁定代理**，让代理保持开启：

```powershell
# 1. 确保您的代理软件（Clash 等）正在运行
# 2. 在 PowerShell 中运行
Lock-Proxy
```

**效果**：
- ✅ 代理将永久保持开启，不跟随系统代理开关
- ✅ 所有新打开的终端都会自动使用代理
- ✅ Claude Code 随时可用，无需担心连接问题

**解锁（恢复自动检测）**：
```powershell
Unlock-Proxy
```

### 方案 2：手动管理代理

如果您需要灵活控制代理：

```powershell
# 开启代理（当前会话）
Enable-Proxy

# 关闭代理（当前会话）
Disable-Proxy

# 重新检测系统代理状态
Set-AutoProxy

# 查看代理状态
Get-ProxyStatus  # 或 proxy-status
```

## 快速命令参考

| 命令 | 功能 | 说明 |
|------|------|------|
| `Lock-Proxy` | 锁定代理 | 代理保持开启，不跟随系统设置 |
| `Unlock-Proxy` | 解锁代理 | 恢复自动检测系统代理开关 |
| `Set-AutoProxy` | 重新检测代理 | 根据系统代理开关更新环境变量 |
| `Get-ProxyStatus` | 查看代理状态 | 显示所有代理配置 |
| `Sync-ProxyToTools` | 同步到工具 | 将代理同步到 git/npm/scoop |

## 使用建议

### 场景 1：日常开发（推荐）

```powershell
# 一次性设置，长期有效
Lock-Proxy

# 现在可以随意开关系统代理，Claude Code 始终可用
```

### 场景 2：偶尔使用 Claude Code

```powershell
# 使用前确保代理开启
# 在 PowerShell 中检查
Get-ProxyStatus

# 如果代理未设置，手动开启
Enable-Proxy
```

### 场景 3：切换代理状态后

**重要**：切换代理状态后，需要在**新的终端窗口**中启动 Claude Code！

1. 关闭旧的终端窗口
2. 打开新的终端（会重新加载 Profile）
3. 启动 Claude Code

或者直接使用锁定模式，避免这个问题。

## 验证代理配置

运行测试脚本：
```powershell
python test_setup.py
```

手动测试连接：
```powershell
# 测试代理是否工作
curl -I https://api.anthropic.com

# 如果返回 "200 Connection established" 或 "404"，说明代理正常
# 如果返回 "403 Forbidden"，说明是直连（被墙）
```

## 故障排查

### Q: 锁定代理后，仍然无法连接？

**A**: 检查代理软件是否正在运行：
```powershell
# 测试代理端口
curl -x http://127.0.0.1:33210 -I https://www.google.com
```

如果失败，说明代理软件未运行或端口不对。

### Q: 想要临时关闭代理怎么办？

**A**:
```powershell
# 如果已锁定，先解锁
Unlock-Proxy

# 关闭系统代理开关

# 打开新的终端窗口
# 现在代理已关闭
```

### Q: 不同终端（PowerShell/Git Bash）代理配置不一致？

**A**: 用户级环境变量对所有程序生效，但**需要重启程序才能读取新值**。

解决方法：
1. 关闭所有旧终端
2. 打开新终端
3. 或者使用 `Lock-Proxy` 避免这个问题

## 代理地址配置

如果您的代理地址不是 `127.0.0.1:33210`，修改 Profile：

```powershell
# 编辑 Profile
notepad $PROFILE

# 修改这三行
$PROXY_HTTP = "http://127.0.0.1:YOUR_PORT"
$PROXY_SOCKS = "socks5://127.0.0.1:YOUR_PORT"
$PROXY_HOST_PORT = "127.0.0.1:YOUR_PORT"

# 保存后重新加载
. $PROFILE
```

## 总结

- ✅ **推荐**：使用 `Lock-Proxy` 锁定代理，一劳永逸
- ⚠ 切换代理状态后，必须在新终端中启动 Claude Code
- ⚠ 在中国大陆使用 Claude Code 必须使用代理
