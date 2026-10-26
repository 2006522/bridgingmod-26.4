"""校验一个 mod jar 引用的原版字段/方法在目标 client.jar 里是否真的存在（含父类/接口继承）。

只做静态检查：能抓出"类搬包 / 成员改名 / 描述符变化"这类会在运行期 NoSuchFieldError /
NoSuchMethodError 的问题。
"""
import struct
import sys
import zipfile

from patch_class import parse_constant_pool


def parse_members(data, pos, pool):
    """解析 fields 或 methods 表，返回 [(name, desc)] 和结束位置。"""
    (count,) = struct.unpack('>H', data[pos:pos + 2])
    pos += 2
    out = []
    for _ in range(count):
        _acc, name_idx, desc_idx, attr_count = struct.unpack('>HHHH', data[pos:pos + 8])
        pos += 8
        for _ in range(attr_count):
            (_an,) = struct.unpack('>H', data[pos:pos + 2])
            (alen,) = struct.unpack('>I', data[pos + 2:pos + 6])
            pos += 6 + alen
        name = pool[name_idx]['raw'].decode('utf-8', 'surrogateescape')
        desc = pool[desc_idx]['raw'].decode('utf-8', 'surrogateescape')
        out.append((name, desc))
    return out, pos


def class_info(data):
    pool, pos = parse_constant_pool(data, 8)
    pos += 2  # access_flags
    this_class, super_class = struct.unpack('>HH', data[pos:pos + 4])
    pos += 4
    name = pool[pool[this_class]['idx']]['raw'].decode('utf-8', 'surrogateescape')
    super_name = (pool[pool[super_class]['idx']]['raw'].decode('utf-8', 'surrogateescape')
                  if super_class else None)
    (icount,) = struct.unpack('>H', data[pos:pos + 2])
    pos += 2
    ifaces = []
    for _ in range(icount):
        idx = struct.unpack('>H', data[pos:pos + 2])[0]
        pos += 2
        ifaces.append(pool[pool[idx]['idx']]['raw'].decode('utf-8', 'surrogateescape'))
    fields, pos = parse_members(data, pos, pool)
    methods, pos = parse_members(data, pos, pool)
    return {
        'name': name,
        'super': super_name,
        'interfaces': ifaces,
        'fields': set(fields),
        'methods': set(methods),
    }


def collect_refs(jar_path):
    """收集 jar 里引用的 (owner, name, desc, kind)。"""
    z = zipfile.ZipFile(jar_path)
    refs = set()
    for n in z.namelist():
        if not n.endswith('.class'):
            continue
        data = z.read(n)
        try:
            pool, _ = parse_constant_pool(data, 8)
        except Exception:
            continue
        for item in pool[1:]:
            if item is None:
                continue
            if item['tag'] in (9, 10, 11):  # Fieldref / Methodref / InterfaceMethodref
                raw = item['raw']
                cls_idx, nat_idx = struct.unpack('>HH', raw[:4])
                cls = pool[cls_idx]
                if cls['tag'] != 7:
                    continue
                owner = pool[cls['idx']]['raw'].decode('utf-8', 'surrogateescape')
                nat = pool[nat_idx]
                if nat['tag'] != 12:
                    continue
                nidx, didx = struct.unpack('>HH', nat['raw'][:4])
                name = pool[nidx]['raw'].decode('utf-8', 'surrogateescape')
                desc = pool[didx]['raw'].decode('utf-8', 'surrogateescape')
                kind = 'field' if item['tag'] == 9 else 'method'
                refs.add((owner, name, desc, kind))
    return refs


def main(mod_jar, client_jar):
    zc = zipfile.ZipFile(client_jar)
    ids = {}
    for n in zc.namelist():
        if n.endswith('.class'):
            ids[n[:-6]] = None

    cache = {}

    def info(name):
        if name in cache:
            return cache[name]
        if name not in ids:
            cache[name] = None
            return None
        r = class_info(zc.read(name + '.class'))
        cache[name] = r
        return r

    def has_member(cls, name, desc, kind):
        seen = set()
        stack = [cls]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            ci = info(cur)
            if ci is None:
                continue
            table = ci['fields'] if kind == 'field' else ci['methods']
            if (name, desc) in table:
                return True
            if ci['super']:
                stack.append(ci['super'])
            stack.extend(ci['interfaces'])
        return False

    refs = collect_refs(mod_jar)
    mc_refs = [r for r in refs if r[0].startswith('net/minecraft/')]
    missing = []
    for owner, name, desc, kind in sorted(mc_refs):
        if owner not in ids:
            missing.append((owner, name, desc, kind, '类不存在'))
            continue
        if not has_member(owner, name, desc, kind):
            # 再宽松试一次：同名但描述符不同（多数是签名微调）
            ci = info(owner)
            same_name = False
            seen = set()
            stack = [owner]
            while stack:
                cur = stack.pop()
                if cur in seen:
                    continue
                seen.add(cur)
                ci2 = info(cur)
                if ci2 is None:
                    continue
                table = ci2['fields'] if kind == 'field' else ci2['methods']
                if any(n == name for n, d in table):
                    same_name = True
                    break
                if ci2['super']:
                    stack.append(ci2['super'])
                stack.extend(ci2['interfaces'])
            missing.append((owner, name, desc, kind, '签名不同' if same_name else '成员不存在'))

    print('原版成员引用总数:', len(mc_refs))
    print('缺失:', len(missing))
    for m in missing[:80]:
        print('  %-6s %s.%s %s  [%s]' % (m[3], m[0].replace('/', '.'), m[1], m[2], m[4]))
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
