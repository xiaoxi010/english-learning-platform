# gaokao_json_parts.py — 超大志愿 JSON 拆成主文件 + .part2.json，加载时自动合并
"""Git 单文件限制约 100MB；超过阈值时拆成两个文件，业务代码仍按一个数据集读写。"""
import json
import os

# 留余量，避免 indent 与平台差异顶到 100MB
MAX_PART_BYTES = 95 * 1024 * 1024


def json_part2_path(json_path):
    base, ext = os.path.splitext(json_path)
    return f'{base}.part2{ext or ".json"}'


def has_part2(json_path):
    return os.path.isfile(json_part2_path(json_path))


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _payload_bytes(payload):
    return len(json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'))


def _remove_part2(json_path):
    part2 = json_part2_path(json_path)
    if os.path.isfile(part2):
        os.remove(part2)


def _find_split_index(records, base_payload, max_bytes):
    """二分找分割点，使 part1、part2 都不超过 max_bytes。"""
    total = len(records)
    if total <= 1:
        return total

    lo, hi = 1, total - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        part1 = dict(base_payload)
        part1['records'] = records[:mid]
        part1['split_parts'] = 2
        part2 = {
            'part': 2,
            'parent': os.path.basename(base_payload.get('_json_path') or ''),
            'count': total - mid,
            'records': records[mid:],
        }
        s1 = _payload_bytes(part1)
        s2 = _payload_bytes(part2)
        if s1 <= max_bytes and s2 <= max_bytes:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1

    if best is not None:
        return best

    # 无法在同一 mid 下两边都达标时，优先保证 part1 不超限
    for mid in range(total - 1, 0, -1):
        part1 = dict(base_payload)
        part1['records'] = records[:mid]
        part1['split_parts'] = 2
        part2 = {
            'part': 2,
            'parent': os.path.basename(base_payload.get('_json_path') or ''),
            'count': total - mid,
            'records': records[mid:],
        }
        if _payload_bytes(part1) <= max_bytes and _payload_bytes(part2) <= max_bytes:
            return mid
    return max(1, total // 2)


def save_json_dataset(json_path, payload, max_bytes=MAX_PART_BYTES):
    """写入 JSON；若过大则拆成 json_path + json_path.part2.json。"""
    payload = dict(payload)
    records = list(payload.pop('records', None) or [])
    total = len(records)
    payload['count'] = total
    payload.pop('split_parts', None)

    base_payload = dict(payload)
    base_payload['_json_path'] = json_path

    single = dict(payload)
    single['records'] = records
    if _payload_bytes(single) <= max_bytes or total == 0:
        _write_json(json_path, single)
        _remove_part2(json_path)
        return single

    split_at = _find_split_index(records, base_payload, max_bytes)
    part1 = dict(payload)
    part1['records'] = records[:split_at]
    part1['split_parts'] = 2
    part1['count'] = total

    part2 = {
        'part': 2,
        'parent': os.path.basename(json_path),
        'count': total - split_at,
        'records': records[split_at:],
    }
    _write_json(json_path, part1)
    _write_json(json_part2_path(json_path), part2)

    merged = dict(part1)
    merged['records'] = records
    merged.pop('split_parts', None)
    return merged


def load_json_dataset(json_path):
    """读取 JSON；若存在 .part2 则合并 records。"""
    if not os.path.isfile(json_path):
        return None
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    part2_path = json_part2_path(json_path)
    if int(data.get('split_parts') or 0) >= 2 and os.path.isfile(part2_path):
        with open(part2_path, 'r', encoding='utf-8') as f:
            part2 = json.load(f)
        merged = dict(data)
        records = list(data.get('records') or [])
        records.extend(part2.get('records') or [])
        merged['records'] = records
        if not merged.get('count'):
            merged['count'] = len(records)
        return merged
    return data


def dataset_file_count(json_path):
    """从主文件读取条数，拆分数据集不加载 part2。"""
    if not os.path.isfile(json_path):
        return 0
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = data.get('count')
        if count is not None:
            return int(count)
        return len(data.get('records') or [])
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return 0


def copy_json_dataset(src_path, dest_path):
    """复制数据集（含 part2）。"""
    if not os.path.isfile(src_path):
        return
    os.makedirs(os.path.dirname(dest_path) or '.', exist_ok=True)
    with open(src_path, 'rb') as fsrc, open(dest_path, 'wb') as fdst:
        fdst.write(fsrc.read())
    part2_src = json_part2_path(src_path)
    part2_dest = json_part2_path(dest_path)
    if os.path.isfile(part2_src):
        with open(part2_src, 'rb') as fsrc, open(part2_dest, 'wb') as fdst:
            fdst.write(fsrc.read())
    elif os.path.isfile(part2_dest):
        os.remove(part2_dest)


def split_json_file_if_needed(json_path, max_bytes=MAX_PART_BYTES):
    """就地拆分已有单文件 JSON（若超过阈值）。"""
    if not os.path.isfile(json_path):
        return False
    if has_part2(json_path):
        return False
    size = os.path.getsize(json_path)
    if size <= max_bytes:
        return False
    with open(json_path, 'r', encoding='utf-8') as f:
        payload = json.load(f)
    save_json_dataset(json_path, payload, max_bytes=max_bytes)
    return True
