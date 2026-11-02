# DSH FlexSim MCP

由原 DSH FlexSim MCP 整理和修复的 **DeepSeek Harness 插件包**。通过 DSH 官方 MCP client bridge 调用本机 FlexSim，支持脚本执行确认、中文文件、模型保存备份和 CSV 读取。

仓库：[w2cemm/dsh-flexsim-mcp](https://github.com/w2cemm/dsh-flexsim-mcp)。这是 DSH 独立项目；此前的 [Codex 插件仓库](https://github.com/w2cemm/flexsim-mcp) 单独保留。代码最初在 DSH 中开发，本版本补充兼容性修复和安装验证。

代码采用 [MIT 许可证](LICENSE) 开源，允许使用、修改和分发，须保留版权与许可声明。FlexSim 本体及其他依赖遵循各自许可。

## 环境

- Windows 10/11；DeepSeek Harness 0.2.1-rc.3 或兼容的 0.2.x 版本，Node 22+。
- Python 3.10+，标准库即可；DSH 自带 Python 3.12 也可使用。
- 单独安装并合法授权的 FlexSim；当前按钮偏移在本机显示为 FlexSim 2022 的安装上验证，默认可执行文件目录为 FlexSim 2023。
- 已安装的 elevated companion，或本仓库 `companion/` 中的桥接代码。

仓库不包含 FlexSim 程序、许可、用户模型、仿真结果、个人配置或登录凭据。

## 推荐安装方式：复用现有 companion

克隆仓库，在根目录执行：

```powershell
python scripts/install_dsh.py --companion "C:\path\to\existing\companion" --workspace "C:\path\to\model-workspace" --dry-run
python scripts/install_dsh.py --companion "C:\path\to\existing\companion" --workspace "C:\path\to\model-workspace"
```

如果 `dsh` 不在 PATH 中，给 `--dsh` 传 DSH CLI 的绝对路径。Desktop 通常在其安装目录的 `resources/runtime/cli/bin/dsh.cmd`。

脚本会备份该 profile 的四份配置文件，调用官方 `dsh plugin --profile desktop add <本仓库>`，将旧的单条 `flexsim-mcp-bridge` 手工插入块迁移成对 bundle 行的配置覆盖。它只修改这条 FlexSim 配置；如发现共享插入块或重复条目，会停止迁移并保留备份。安装记录位于 `.local/installation.json`，备份位于 `.local/backups/`，这些内容不进入 GitHub。

脚本写入本次 Python 的绝对路径，避免 DSH Desktop 继承旧 PATH 时找错解释器；同时设置明确的 workspace、companion、共享 runtime 和 15 分钟桥接超时。重启 DSH 后加载新连接。安装不会创建、修改或重启管理员计划任务。

## 直接安装 bundle

```powershell
dsh plugin --profile desktop add github:w2cemm/dsh-flexsim-mcp
dsh --profile desktop --dump-config
```

代码已经是 JavaScript，不需要构建脚本或安装时编译。直接安装不会迁移旧的手工 `flexsim-mcp-bridge`，也不会自动发现旧 companion。已有旧配置时请使用上面的安装脚本，或先审阅并手动迁移该单条配置，避免同一 namespace 的重复连接。

可以在 profile 的 `cordis.patch.yml` 中覆盖 bundle 行：

```yaml
- id: flexsim-mcp-bridge
  config:
    python: 'C:\path\to\python.exe'
    companionDir: 'C:\path\to\companion'
    runtimeDir: 'C:\path\to\shared\flexsim-mcp\runtime'
    workspaceDir: 'C:\path\to\model-workspace'
    toolCallTimeoutMs: 900000
```

`flexsimExe` 可指定 FlexSim 程序，但必须同时被 companion 的 `$ExeAllow` 白名单允许。多个客户端操作同一 companion 时，应使用相同 runtime，使桌面文件锁生效。DSH adapter 使用 `import.meta.url` 定位随包文件，普通克隆、链接安装及含空格路径均可使用。

## 首次安装 companion

没有现成 companion 时，先审阅 `companion/install.ps1`、`worker.ps1`，再自行运行 `companion/install.cmd` 并接受 UAC。它设置文件队列 ACL，并注册当前用户的管理员登录任务 `DSH_ElevCompanion`。已有同名任务时复用其原目录，避免替换原任务。worker 保留原 DSH 的通用桌面动作及可选 windows-mcp 支持；FlexSim 功能只使用所需动作，不要求安装 windows-mcp。

`companion/start.cmd` 启动已登记的任务，`companion/uninstall.ps1` 移除任务。插件登记和提权任务安装是独立操作。

## 工具与运行规则

| 工具 | 用途 |
|---|---|
| `flexsim_status` | companion 心跳和 FlexSim 窗口 |
| `flexsim_open` | 打开 FlexSim 或模型 |
| `flexsim_set_script` | 写入脚本，不运行 |
| `flexsim_run_script` | `path` 或 `text` 二选一，运行并验证唯一完成标记 |
| `flexsim_console` | 读取可访问的诊断面板；部分版本不暴露 `print()` 输出 |
| `flexsim_save` | 绝对 `.fsm` 路径；默认拒绝覆盖，显式覆盖先备份并返回 SHA-256 |
| `flexsim_stats` | 读取模型导出的 CSV |
| `flexsim_close` | 关闭 FlexSim，应先保存模型 |

DSH 中的工具名称为 `mcp__flexsim__flexsim_run_script` 等。应先 `flexsim_open`，再运行脚本；大段脚本建议先保存为 UTF-8 文件，使用 `path` 参数。相对脚本路径相对于 `workspaceDir`，与客户端从哪里启动无关。

`verified=true` 只表示脚本到达结尾。异步 `go()` 仿真必须另查停止状态或导出文件；提前 `return`、编译失败和超时不会被当成成功，也不会自动重试可能已有副作用的脚本。脚本允许最长 600 秒，桥接允许 900 秒，为窗口操作和返回诊断预留时间。

工具栏仍需按版本、DPI 和布局在 `flexsim-mcp/config.json` 校准。运行凭据、临时脚本和锁存放在 runtime。JSON 格式错误或无效 UTF-8 会返回协议错误；已经损坏的 Unicode 内容会被明确拒绝，插件不猜测恢复用户脚本。

## 在其他 MCP 客户端中复用

服务仍使用标准 stdio，也可在 Codex 中验证：

```toml
[mcp_servers.flexsim]
command = 'C:\path\to\python.exe'
args = ['-X', 'utf8', 'C:\path\to\dsh-flexsim-mcp\scripts\launch.py']
startup_timeout_sec = 60
tool_timeout_sec = 900

[mcp_servers.flexsim.env]
FLEXSIM_COMPANION_DIR = 'C:\path\to\companion'
FLEXSIM_WORKSPACE_DIR = 'C:\path\to\model-workspace'
FLEXSIM_MCP_RUNTIME_DIR = 'C:\path\to\shared\flexsim-mcp\runtime'
```

启动器也读取 `%LOCALAPPDATA%/FlexSimMCP/settings.json`；明确传入的环境变量优先。该文件可包含上述三个变量、`FLEXSIM_EXE` 和 `FLEXSIM_MCP_LOG`。可通过 `FLEXSIM_MCP_SETTINGS` 更换个人设置文件。

## 测试

```powershell
python -m unittest discover -s flexsim-mcp -p "test_*.py" -v
python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/bridge.test.mjs
```

测试覆盖编辑器识别、中文脚本、完成标记、覆盖保护、MCP 无效帧后的恢复、长 Unicode 请求、稳定工作目录、通知不触发桌面动作、DSH bridge 配置和旧 profile 行迁移。GUI 执行仍需要本机 FlexSim、companion 和正确坐标。

插件格式和安装方式依据 [DSH 官方打包文档](https://deepseek-harness.github.io/deepseek-harness/en/develop/basic/publish) 和 [官方 MCP client 文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md)。本项目发布到 GitHub，未发布到 npm 或任何公共插件市场。
