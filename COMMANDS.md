# 重要提示：PowerShell 命令使用说明

## ⚠️ 命令名称格式

本项目中的 PowerShell 命令使用以下命名规则：

### 函数名称（必须使用首字母大写）

```powershell
Lock-Proxy          # ✅ 正确
Unlock-Proxy        # ✅ 正确
Get-ProxyStatus     # ✅ 正确
Set-AutoProxy       # ✅ 正确
```

```powershell
lock-proxy          # ❌ 错误 - 会提示找不到命令
unlock-proxy        # ❌ 错误 - 会提示找不到命令
```

### 别名（全小写-连字符）

```powershell
proxy-status        # ✅ 正确（Get-ProxyStatus 的别名）
proxy-sync          # ✅ 正确（Sync-ProxyToTools 的别名）
```

## 🔍 为什么会这样？

PowerShell 在 Windows 上对大小写不敏感，但 **别名和函数名不能相同**（即使大小写不同）。

之前的配置尝试创建这样的别名：
```powershell
Set-Alias -Name lock-proxy -Value Lock-Proxy  # ❌ 错误
function Lock-Proxy { ... }
```

这会导致循环引用，PowerShell 无法正确解析命令。

**解决方案**：
- `Lock-Proxy` 和 `Unlock-Proxy` **只作为函数使用**，不创建别名
- 其他命令提供小写别名（如 `proxy-status`）

## 📖 完整命令列表

### 代理管理命令

| 函数名 | 别名 | 说明 |
|--------|------|------|
| `Lock-Proxy` | 无 | 锁定代理（不跟随系统设置） |
| `Unlock-Proxy` | 无 | 解锁代理（恢复自动检测） |
| `Get-ProxyStatus` | `proxy-status` | 查看代理状态 |
| `Sync-ProxyToTools` | `proxy-sync` | 同步代理到 git/npm/scoop |
| `Set-AutoProxy` | 无 | 重新检测代理状态 |
| `Enable-Proxy` | 无 | 手动开启代理 |
| `Disable-Proxy` | 无 | 手动关闭代理 |

### 使用示例

```powershell
# 锁定代理（推荐用于 Claude Code）
Lock-Proxy

# 查看代理状态（两种方式都可以）
Get-ProxyStatus
proxy-status

# 解锁代理
Unlock-Proxy

# 同步代理到工具（两种方式都可以）
Sync-ProxyToTools
proxy-sync
```

## 🔄 重新加载 Profile

如果您在旧的 PowerShell 会话中遇到命令找不到的问题，请重新加载 Profile：

```powershell
. $PROFILE
```

或者关闭当前终端，打开新的 PowerShell 窗口。

## 💡 故障排查

### 问题：提示 `Lock-Proxy` 找不到

```powershell
PS> Lock-Proxy
Lock-Proxy: The term 'lock-proxy' is not recognized...
```

**解决方法**：

1. 确保使用 **首字母大写**：`Lock-Proxy`（不是 `lock-proxy`）

2. 重新加载 Profile：
   ```powershell
   . $PROFILE
   ```

3. 检查函数是否加载：
   ```powershell
   Get-Command Lock-Proxy -CommandType Function
   ```

   应该输出：
   ```
   CommandType    Name          Version    Source
   -----------    ----          -------    ------
   Function       Lock-Proxy
   ```

4. 如果仍然不行，运行 `python setup.py` 重新配置

### 问题：旧版本配置冲突

如果您之前安装过旧版本，可能存在别名冲突。解决方法：

```powershell
# 删除可能存在的冲突别名
Remove-Alias lock-proxy -ErrorAction SilentlyContinue
Remove-Alias unlock-proxy -ErrorAction SilentlyContinue

# 重新加载 Profile
. $PROFILE
```

---

**记住**：使用 `Lock-Proxy`（首字母大写），不要使用 `lock-proxy`（全小写）！✅
