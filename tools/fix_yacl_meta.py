"""把 YACL 的 minecraft 版本约束放宽 —— 它原本是 ~26.4-（只认 26.4 的正式/预发布），
改类名之后其他都兼容，放宽到 >=26.3 免得 Loader 的版本比较出意外。
"""
import json
import zipfile

SRC = r'C:\Users\wnw\AppData\Local\Temp\yacl-3.9.9+26.4-patched.jar'
DST = r'C:\Users\wnw\AppData\Local\Temp\yacl-3.9.9+26.4-final.jar'

zin = zipfile.ZipFile(SRC)
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for info in zin.infolist():
        data = zin.read(info.filename)
        if info.filename == 'fabric.mod.json':
            cfg = json.loads(data.decode('utf-8'))
            print('原依赖:', cfg['depends'])
            cfg['depends']['minecraft'] = '>=26.3'
            print('改后:', cfg['depends'])
            data = json.dumps(cfg, ensure_ascii=False).encode('utf-8')
        zout.writestr(info, data)
print('输出:', DST)
