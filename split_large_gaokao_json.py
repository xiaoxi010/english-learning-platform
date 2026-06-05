#!/usr/bin/env python3
"""将 data/gaokao_apply 下超过 100MB 的 JSON 拆成主文件 + .part2.json"""
import os
import sys

from gaokao_json_parts import MAX_PART_BYTES, json_part2_path, split_json_file_if_needed
from gaokao_province_registry import GAOKAO_DATA_DIR, PROVINCES_DIR

LIMIT = 100 * 1024 * 1024


def iter_json_files():
    roots = [GAOKAO_DATA_DIR]
    if os.path.isdir(PROVINCES_DIR):
        for prov in sorted(os.listdir(PROVINCES_DIR)):
            roots.append(os.path.join(PROVINCES_DIR, prov))
    seen = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            if not name.endswith('.json') or name.endswith('.part2.json'):
                continue
            if name == 'manifest.json':
                continue
            path = os.path.join(root, name)
            if path in seen or not os.path.isfile(path):
                continue
            seen.add(path)
            yield path


def main():
    split_count = 0
    for path in iter_json_files():
        size = os.path.getsize(path)
        if size <= LIMIT and not path.endswith('.part2.json'):
            continue
        if split_json_file_if_needed(path, max_bytes=MAX_PART_BYTES):
            p2 = json_part2_path(path)
            s1 = os.path.getsize(path)
            s2 = os.path.getsize(p2) if os.path.isfile(p2) else 0
            print(f'SPLIT  {path}')
            print(f'       part1 {s1/1024/1024:.1f} MB  part2 {s2/1024/1024:.1f} MB')
            split_count += 1
    print(f'done, split {split_count} file(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
