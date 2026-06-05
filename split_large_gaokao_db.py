#!/usr/bin/env python3
"""将超过 100MB 的省份数据库拆成 part2（本科库与其余批次库分别处理）。"""
import os
import sys

from gaokao_db import (
    MAX_DB_BYTES,
    OTHER_DB_NAME,
    UNDERGRADUATE_DB_NAME,
    db_part2_path,
    province_db_other,
    province_db_undergraduate,
    split_db_file_if_needed,
)
from gaokao_jilin_data_loader import EXPERT_FIELDS, STRONG_BASE_FIELDS, rebuild_datasets_registry
from gaokao_province_registry import PROVINCES_DIR

EXPERT_KEYS = [k for k, _ in EXPERT_FIELDS]
STRONG_KEYS = [k for k, _ in STRONG_BASE_FIELDS]
LIMIT = 100 * 1024 * 1024


def main():
    if not os.path.isdir(PROVINCES_DIR):
        print('provinces dir missing')
        return 1
    split_count = 0
    for name in sorted(os.listdir(PROVINCES_DIR)):
        root = os.path.join(PROVINCES_DIR, name)
        if not os.path.isdir(root):
            continue
        for label, main in (
            ('undergraduate', province_db_undergraduate(name)),
            ('other', province_db_other(name)),
        ):
            if not os.path.isfile(main):
                continue
            before = os.path.getsize(main)
            part2 = db_part2_path(main)
            if before <= LIMIT and not os.path.isfile(part2):
                continue
            if split_db_file_if_needed(name, main, EXPERT_KEYS, STRONG_KEYS, max_bytes=MAX_DB_BYTES):
                s1 = os.path.getsize(main) / 1024 / 1024
                s2 = os.path.getsize(part2) / 1024 / 1024 if os.path.isfile(part2) else 0
                print(f'SPLIT {name} {label}: part1 {s1:.1f} MB  part2 {s2:.1f} MB')
                split_count += 1
    rebuild_datasets_registry()
    print(f'done: split {split_count} db file(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
