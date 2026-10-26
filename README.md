# 搭桥辅助 (Bridging Mod) 26.4-snapshot-5 适配版

把 [BridgingMod](https://github.com/squeeglii/BridgingMod) 2.7.0 和它依赖的
[YACL](https://github.com/isXander/YetAnotherConfigLib) 移植到
**Minecraft 26.4-snapshot-5 / Fabric 0.19.5+**。

> ⚠️ **这不是官方版本**，是我自己改的。原作者的 Modrinth / GitHub 版本只到 26.3。
> 有问题请在本仓库提，不要去打扰原作者。

---

## 这是什么

[BridgingMod](https://modrinth.com/mod/bridging-mod) 是一个基岩版风格的搭桥辅助：
看着方块边缘按住右键，它会自动把方块放到你脚下那一格，横穿峡谷、岩浆、虚空时
不用回头蹲下、准星对着脚下方块、一边退一边点。

它的最新版本（2.7.0）是为 **26.3** 编译的，直接丢进 **26.4-snapshot-5** 会加载失败。
这个仓库记录了让它跑起来需要改的每一处，以及打补丁用的脚本。

## 下载

到 [Releases](../../releases) 下载两个 jar，一起放进 `mods/`：

| 文件 | 说明 |
| --- | --- |
| `BridgingMod-2.7.0-mc26.4.jar` | 搭桥辅助本体（装进去显示名是「搭桥辅助(Bridging Mod)」） |
| `YACL-3.9.9-mc26.4.jar` | 配置库（装进去显示名是「配置库(YACL)」），BridgingMod 依赖它 |

原来的 Fabric API、游戏本体、Fabric Loader 照旧。

**两个都要装**，BridgingMod 的 `fabric.mod.json` 里 `depends` 写了 `yet_another_config_lib_v3`。

## 改了什么

### BridgingMod 2.7.0+26.3 → 2.7.0+26.4-snapshot5

| # | 改动 | 原因 |
| --- | --- | --- |
| 1 | `net/minecraft/client/renderer/RenderPipelines` → `net/minecraft/client/renderer/pipeline/RenderPipelines` | snapshot-5 把它挪包了 |
| 2 | `com/mojang/renderpearl/api/pipeline/RenderPipeline` → `com/mojang/blaze3d/pipeline/RenderPipeline` | snapshot-5 把 renderpearl 的 `RenderPipeline` 合并回 blaze3d |
| 3 | 重写 `CrosshairRenderingMixin` 的注入签名 | `Hud#extractCrosshair` 从 `(GuiGraphicsExtractor, DeltaTracker)` 变成了单参数 |

第 1、2 条是改 class 常量池里的类名（`tools/patch_class.py`）。

第 3 条改的是字节码本身（`tools/FixCrosshairMixin.java`，用 ASM）：

- `DeltaTracker` 这个参数在 handler 里**一次都没被读过**（局部变量从 slot 4 才开始用），
  所以删掉它只需要把后面的槽位整体前移一格；
- 一起改的还有：方法描述符、19 处 `VarInsn` / `IincInsn` 的槽位号、每个栈帧的 `local` 列表、
  局部变量调试表、`maxLocals`、以及 `@Inject(method="…")` 注解里的描述符字符串；
- **栈帧必须手动同步**，不然校验器会认为帧和 `maxLocals` 对不上；
- 写回用 `ClassWriter(0)`（不重算帧）—— `COMPUTE_FRAMES` 需要 `getCommonSuperClass`，
  会去加载原版类，环境里加载不到。

验证方式：`tools/CheckFrames.java` dump 出 `maxLocals=10`、帧 `local` 为
`[this, extractor, CallbackInfo, int, Direction, alignment, int×4]`，再用
`CheckClassAdapter.verify` 做结构校验。

### YACL 3.9.9+26.4-snapshot-3 → 3.9.9+26.4

| # | 改动 | 原因 |
| --- | --- | --- |
| 1 | `RenderPipelines` 类名同上（9 个 class） | 同一条搬包 |
| 2 | `fabric.mod.json` 的 `minecraft: ~26.4-` 放宽成 `>=26.3` | 免得 Loader 版本比较出意外 |

两个 jar 的 `name` 都改成了中文显示名。

## 已知问题

- **配置界面可能画不出来。** YACL 覆写的 `Screen#extractRenderState`、
  `EditBox#extractWidgetRenderState`、`ContainerObjectSelectionList#extractWidgetRenderState`
  在 snapshot-5 里都改成单参数了，旧的 4 参数覆写不会生效，界面会是空白。
  **搭桥功能本身不受影响**，默认配置就能用。
- 点配置里的按钮有可能报 `NoSuchFieldError`：`SoundEvents.UI_BUTTON_CLICK` 的类型从
  `Holder$Reference` 变成了 `Holder`。
- 准星方向指示默认是开的（`showCrosshair = true`）。它画在准星四周，指示方块会往
  上 / 水平 / 下放。

## 需要重新打补丁时

`tools/` 里的脚本可以复用，前提是你手边有对应版本的 `client.jar`（26.x 未混淆）：

```bash
# 1. 扫一遍 mod 引用的原版类/成员是否存在
python tools/check_refs.py <mod.jar> <client.jar>

# 2. 改常量池里的类名
python tools/patch_class.py <in.jar> <out.jar> "旧/类名=新/类名"

# 3. 改方法签名（这里是准星 mixin 的例子，按需改常量）
javac -cp asm.jar;asm-tree.jar tools/FixCrosshairMixin.java
java -cp .;asm.jar;asm-tree.jar FixCrosshairMixin <in.class> <out.class>
```

`check_refs.py` 会递归追父类和接口，报「类不存在 / 成员不存在 / 签名不同」三级。
`Direction.ordinal()` 这类是假阳性（enum 的 final 方法在 JDK 的 `Enum` 里）。

## 许可证

本仓库里的补丁脚本用 MIT。

打包的 jar 是原作的修改版，遵循各自原许可证：

- BridgingMod：MIT，作者 CG360 / squeeglii
- YetAnotherConfigLib (YACL)：LGPL-3.0-or-later，作者 isXander

两个都是允许修改和再分发的。修改内容就是上面那张表，没有别的。
如果原作者发布了自己的 26.4 版本，**请优先用官方的**。
