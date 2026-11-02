# Validation

2026-11-02，版本 1.2.0：

- 29 项既有可靠性测试、8 项传输与安装迁移测试、2 项 Node bridge 测试。
- Windows 系统 Python 3.13 与 DSH 自带 Python 3.12 分别验证 Python 回归。
- 使用实际 DSH CLI 在隔离的 `DSH_HOME` 中安装 bundle；`--dump-config` 确认配置组合；`--dump-config-schema` 确认 DSH 实际导入本包并获取 Config schema。
- Desktop profile 使用官方 CLI 完成 bundle 登记，并迁移为单条 FlexSim 配置覆盖。Desktop 由 Electron 管理，CLI 无权启动该 profile；安装记录明确标记需要重启 Desktop。
- 使用实际 elevated companion 和 FlexSim，从新 stdio 服务运行 220,169 字节 UTF-8 长脚本，脚本文件名及工作目录包含中文；唯一完成标记通过，导出内容核对通过。
- 保存新的中文及空格路径 `.fsm` 副本，文件非空，返回 SHA-256 与实际文件一致。
- 故意提交编译错误，工具返回错误；随后正常脚本执行完成，未自动重试错误脚本。

运行凭据、模型副本、配置备份、个人 profile 和安装记录仅保存在本机 `.local/`，不随仓库分发。此处记录验证方法与结果，不包含个人路径或模型数据。

已知限制：尚未复现用户原始的每一种脚本失败。旧日志确认存在格式错误被静默丢弃、损坏 Unicode 及操作超时。1.2.0 对这些可确认的问题给出明确错误和更稳定的配置；仍需按 FlexSim 版本、DPI 和窗口布局校准按钮偏移。异步仿真完成状态需由模型另行验证。
