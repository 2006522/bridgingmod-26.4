"""改 class 文件常量池里的类名 —— 用来把旧版本搬包的类名映射到新位置。

class 文件里除了常量池中 utf8 项自身的 u2 长度前缀外，再没有任何绝对偏移，
所以只要重建常量池、把后面的字节原样接上就行。
"""
import struct
import sys

CONST_SIZES = {
    3: 4,   # Integer
    4: 4,   # Float
    5: 8,   # Long
    6: 8,   # Double
    9: 4,   # Fieldref
    10: 4,  # Methodref
    11: 4,  # InterfaceMethodref
    12: 4,  # NameAndType
    15: 3,  # MethodHandle
    16: 2,  # MethodType
    17: 4,  # Dynamic
    18: 4,  # InvokeDynamic
    19: 2,  # Module
    20: 2,  # Package
}


def parse_constant_pool(data, pos):
    """返回 (常量池列表, 结束后位置)。列表第 0 项占位 None，与常量池索引对齐。"""
    (count,) = struct.unpack('>H', data[pos:pos + 2])
    pos += 2
    pool = [None]
    i = 1
    while i < count:
        tag = data[pos]
        pos += 1
        if tag == 1:  # Utf8
            (ln,) = struct.unpack('>H', data[pos:pos + 2])
            pos += 2
            raw = data[pos:pos + ln]
            pos += ln
            pool.append({'tag': 1, 'raw': raw})
        elif tag in (7, 8, 16, 19, 20):  # Class/String/MethodType/Module/Package
            pool.append({'tag': tag, 'idx': struct.unpack('>H', data[pos:pos + 2])[0]})
            pos += 2
        elif tag in (15,):  # MethodHandle
            pool.append({'tag': tag, 'raw': data[pos:pos + 3]})
            pos += 3
        elif tag in CONST_SIZES:
            n = CONST_SIZES[tag]
            pool.append({'tag': tag, 'raw': data[pos:pos + n]})
            pos += n
        else:
            raise ValueError('unknown constant tag %d at %d' % (tag, pos - 1))
        if tag in (5, 6):  # Long/Double 占两个槽位
            pool.append(None)
            i += 1
        i += 1
    return pool, pos


def build_constant_pool(pool):
    out = bytearray()
    out += struct.pack('>H', len(pool))
    for item in pool[1:]:
        if item is None:
            continue
        tag = item['tag']
        out.append(tag)
        if tag == 1:
            raw = item['raw']
            out += struct.pack('>H', len(raw))
            out += raw
        elif tag in (7, 8, 16, 19, 20):
            out += struct.pack('>H', item['idx'])
        else:
            out += item['raw']
    return bytes(out)


def patch(data, mapping):
    """把常量池 utf8 里的 mapping 逐个替换。返回 (新字节, 替换次数)。"""
    pool, after = parse_constant_pool(data, 8)
    hits = 0
    for item in pool[1:]:
        if item is None or item['tag'] != 1:
            continue
        raw = item['raw']
        text = raw.decode('utf-8', 'surrogateescape')
        new = text
        for old, repl in mapping.items():
            if old in new:
                new = new.replace(old, repl)
        if new != text:
            hits += 1
            item['raw'] = new.encode('utf-8', 'surrogateescape')
    if hits == 0:
        return data, 0
    new_pool = build_constant_pool(pool)
    return data[:8] + new_pool + data[after:], hits


def utf8_strings(data):
    pool, _ = parse_constant_pool(data, 8)
    return [i['raw'].decode('utf-8', 'surrogateescape') for i in pool[1:]
            if i is not None and i['tag'] == 1]


if __name__ == '__main__':
    import zipfile
    import os
    import shutil

    if len(sys.argv) < 4:
        print('用法: python patch_class.py <src.jar> <dst.jar> <old=path> [old=path ...]')
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    mapping = {}
    for arg in sys.argv[3:]:
        old, new = arg.split('=', 1)
        mapping[old] = new

    zin = zipfile.ZipFile(src)
    tmp = dst + '.tmp'
    total = 0
    changed_files = 0
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename.endswith('.class'):
                new_data, hits = patch(data, mapping)
                if hits:
                    changed_files += 1
                    total += hits
                data = new_data
            zout.writestr(info, data)
    os.replace(tmp, dst)
    print('改了 %d 个 class，共 %d 处' % (changed_files, total))
