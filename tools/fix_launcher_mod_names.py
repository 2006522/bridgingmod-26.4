"""把 Axolotl 启动器数据库里缓存的 mod 显示名改掉。

为什么需要这个：启动器把 `fabric.mod.json` 的解析结果缓存在
`instance_files.local_mod_data`（一列 JSON），重扫时只刷新 size/sha1/modified_at，
**只要文件路径没变就不重新解析 name** —— 刷新按钮和重启启动器都不会更新它。

所以改完 jar 里的 name 之后，还得把这一列一起改掉。

⚠️ 必须在启动器**完全退出**的状态下运行，否则它退出时会用内存里的值覆盖回去。
"""
import json
import os
import sqlite3
import subprocess
import sys

DB = os.path.join(os.environ['APPDATA'], 'red.ghs.axolotl', 'release', 'app.db')

TARGETS = {
    'BridgingMod-2.7.0+26.4.jar': '搭桥辅助(Bridging Mod)',
    'YACL-3.9.9+26.4.jar': '配置库(YACL)',
}


def launcher_running():
    try:
        out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='ignore').stdout
    except Exception:
        return False
    return 'Axolotl Launcher' in out


def main():
    if launcher_running():
        print('启动器还在运行，先把 Axolotl Launcher 完全退出再跑这个脚本。')
        return 1

    con = sqlite3.connect(DB)
    cur = con.cursor()
    changed = 0
    for filename, new_name in TARGETS.items():
        cur.execute('SELECT id, local_mod_data FROM instance_files WHERE file_name = ?', (filename,))
        rows = cur.fetchall()
        if not rows:
            print('没找到记录:', filename)
            continue
        for rid, raw in rows:
            if not raw:
                continue
            data = json.loads(raw)
            old = data.get('name')
            data['name'] = new_name
            # 保持原来的紧凑格式（separators 不加空格），免得启动器解析出岔子
            cur.execute('UPDATE instance_files SET local_mod_data = ? WHERE id = ?',
                        (json.dumps(data, ensure_ascii=False, separators=(',', ':')), rid))
            print('%s: %r → %r' % (filename, old, new_name))
            changed += 1
    con.commit()
    con.close()
    print('更新了 %d 条记录' % changed)
    return 0


if __name__ == '__main__':
    sys.exit(main())
