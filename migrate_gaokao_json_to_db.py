#!/usr/bin/env python3
"""将各省 JSON 志愿数据迁移为 data.db（每省一个 SQLite 文件）。"""
import os
import sys

from gaokao_db import migrate_json_payload_to_db, province_db_path
from gaokao_json_parts import load_json_dataset
from gaokao_jilin_data_loader import EXPERT_FIELDS, STRONG_BASE_FIELDS, rebuild_datasets_registry
from gaokao_province_registry import PROVINCES_DIR, province_json_path, read_manifest, write_manifest

EXPERT_KEYS = [k for k, _ in EXPERT_FIELDS]
STRONG_KEYS = [k for k, _ in STRONG_BASE_FIELDS]

BATCH_FILES = (
    ('early', 'expert_early.json'),
    ('undergraduate', 'expert_undergraduate.json'),
    ('junior', 'expert_junior.json'),
    ('strong', 'strong_base.json'),
)


def _remove_json(path):
    if os.path.isfile(path):
        os.remove(path)


def migrate_province(province, remove_json=True):
    migrated = []
    counts = {}
    for batch_key, filename in BATCH_FILES:
        json_path = os.path.join(PROVINCES_DIR, province, filename)
        if not os.path.isfile(json_path):
            continue
        payload = load_json_dataset(json_path)
        if not payload:
            continue
        migrate_json_payload_to_db(province, batch_key, payload, EXPERT_KEYS, STRONG_KEYS)
        counts[batch_key] = payload.get('count') or len(payload.get('records') or [])
        migrated.append(filename)
        if remove_json:
            _remove_json(json_path)
            part2 = json_path.replace('.json', '.part2.json')
            _remove_json(part2)
    if not migrated:
        return False
    manifest = read_manifest(province) or {}
    write_manifest(province, {
        **manifest,
        'storage': 'sqlite',
        'db_undergraduate': 'data.undergraduate.db',
        'db_other': 'data.other.db',
        'db_file': 'data.undergraduate.db',
        'counts': {**(manifest.get('counts') or {}), **counts},
    })
    print(f'  {province}: {", ".join(migrated)} -> batch dbs')
    return True


def main():
    if not os.path.isdir(PROVINCES_DIR):
        print('provinces dir missing')
        return 1
    total = 0
    for name in sorted(os.listdir(PROVINCES_DIR)):
        root = os.path.join(PROVINCES_DIR, name)
        if not os.path.isdir(root):
            continue
        if migrate_province(name):
            total += 1
    rebuild_datasets_registry()
    print(f'done: migrated {total} province(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
