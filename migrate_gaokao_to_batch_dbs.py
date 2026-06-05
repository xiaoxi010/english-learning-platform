#!/usr/bin/env python3
"""将各省旧版 data.db 迁移为 data.undergraduate.db + data.other.db。"""
import os
import sys

from gaokao_db import migrate_province_to_batch_dbs, province_has_db
from gaokao_jilin_data_loader import EXPERT_FIELDS, STRONG_BASE_FIELDS, rebuild_datasets_registry
from gaokao_province_registry import PROVINCES_DIR, read_manifest, write_manifest

EXPERT_KEYS = [k for k, _ in EXPERT_FIELDS]
STRONG_KEYS = [k for k, _ in STRONG_BASE_FIELDS]


def main():
    if not os.path.isdir(PROVINCES_DIR):
        print('provinces dir missing')
        return 1
    total = 0
    for name in sorted(os.listdir(PROVINCES_DIR)):
        root = os.path.join(PROVINCES_DIR, name)
        if not os.path.isdir(root):
            continue
        if not province_has_db(name):
            continue
        if migrate_province_to_batch_dbs(name, EXPERT_KEYS, STRONG_KEYS):
            print('migrated', name)
            total += 1
    rebuild_datasets_registry()
    print(f'done: migrated {total} province(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
