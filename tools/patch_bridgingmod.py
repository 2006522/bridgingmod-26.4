"""给 BridgingMod 打 26.4-snapshot-5 兼容补丁。

改动三处：
1. RenderPipelines 搬包：renderer/ → renderer/pipeline/
2. RenderPipeline 从 com.mojang.renderpearl.api.pipeline 合并回 com.mojang.blaze3d.pipeline
3. mixins.json 里去掉 CrosshairRenderingMixin —— 它注入的 Hud#extractCrosshair
   在 snapshot-5 已经从 (GuiGraphicsExtractor, DeltaTracker)V 改成单参数
   (GuiGraphicsExtractor)V，handler 签名也得跟着改（要删参数、重排局部变量），
   不是改字符串能解决的。少了它只丢"准星方向箭头"这一个视觉提示，搭桥本身不受影响。
"""
import json
import zipfile

from patch_class import patch

SRC = r'D:\Users\wnw\Downloads\BridgingMod-2.7.0+26.3.fabric-release.jar'
DST = r'C:\Users\wnw\AppData\Local\Temp\BridgingMod-2.7.0+26.4.jar'

MAPPING = {
    'net/minecraft/client/renderer/RenderPipelines': 'net/minecraft/client/renderer/pipeline/RenderPipelines',
    'com/mojang/renderpearl/api/pipeline/RenderPipeline': 'com/mojang/blaze3d/pipeline/RenderPipeline',
}

DROP_MIXINS = {'CrosshairRenderingMixin'}

zin = zipfile.ZipFile(SRC)
changed = 0
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for info in zin.infolist():
        data = zin.read(info.filename)
        name = info.filename

        if name.endswith('.class'):
            data, hits = patch(data, MAPPING)
            if hits:
                changed += hits

        elif name == 'bridgingmod.mixins.json':
            cfg = json.loads(data.decode('utf-8'))
            before = list(cfg.get('client', []))
            cfg['client'] = [m for m in before if m not in DROP_MIXINS]
            print('mixin client 列表: %s → %s' % (before, cfg['client']))
            data = json.dumps(cfg, indent=2).encode('utf-8')

        elif name == 'fabric.mod.json':
            cfg = json.loads(data.decode('utf-8'))
            cfg['version'] = '2.7.0+26.4-snapshot5'
            # 快照版本号比较：26.4-snapshot-5 满足 >=26.3 和 ~26.4-，不用改 depends
            data = json.dumps(cfg, indent=2, ensure_ascii=False).encode('utf-8')

        zout.writestr(info, data)

print('常量池改动了 %d 处' % changed)
print('输出:', DST)
