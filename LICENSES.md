# 许可证说明

## 本仓库的补丁脚本

`tools/` 下的 Python / Java 脚本：**MIT**。

## 打包分发的 jar

### BridgingMod

- 原作者：CG360 / squeeglii
- 原项目：https://github.com/squeeglii/BridgingMod
- 许可证：MIT
- 本仓库分发的 `BridgingMod-2.7.0+26.4.jar` 是 2.7.0+26.3 的修改版，
  修改内容见 README 的「改了什么」一节（两处类名映射 + 一个 mixin 签名重写）

MIT 许可证允许修改、再分发，但要求保留原版权声明。原 jar 内的
`META-INF/MANIFEST.MF` 与源码中的版权声明均未改动。

### YetAnotherConfigLib (YACL)

- 原作者：isXander
- 原项目：https://github.com/isXander/YetAnotherConfigLib
- 许可证：LGPL-3.0-or-later
- 本仓库分发的 `YACL-3.9.9+26.4.jar` 是 3.9.9+26.4-fabric 的修改版，
  修改内容：9 个 class 的 `RenderPipelines` 类名映射、`minecraft` 依赖范围放宽、
  显示名改为中文

LGPL-3.0 允许修改和再分发。修改点已在 README 中逐条列出；
原项目源码可从上面的链接获取，按 LGPL 要求可对照复现全部改动。

## 如果原作者发布了官方 26.4 版本

请优先使用官方版本。本仓库只是在新快照上让它能跑起来的临时方案。
