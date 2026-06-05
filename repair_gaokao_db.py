#!/usr/bin/env python3
"""合并各省多分片 DB 中的重复记录，并重新平衡拆分（按本科/其余两个库）。"""
import os
import sys

from gaokao_db import (
    OTHER_DB_NAME,
    STRONG_BUCKET,
    UNDERGRADUATE_DB_NAME,
    _close_conns,
    _connect,
    _delete_expert_bucket,
    _delete_strong,
    _ensure_schema,
    _save_meta,
    _vacuum,
    db_part2_path,
    db_part3_path,
    province_db_other,
    province_db_undergraduate,
    split_db_file_if_needed,
)
from gaokao_jilin_data_loader import EXPERT_FIELDS, STRONG_BASE_FIELDS, rebuild_datasets_registry
from gaokao_province_registry import PROVINCES_DIR, read_manifest

EXPERT_KEYS = [k for k, _ in EXPERT_FIELDS]
STRONG_KEYS = [k for k, _ in STRONG_BASE_FIELDS]


def _collect_expert(paths, bucket):
    rows = []
    seen = set()
    cols = EXPERT_KEYS
    for path in paths:
        if not os.path.isfile(path):
            continue
        conn = _connect(path, readonly=True)
        try:
            data = conn.execute(
                f'SELECT {",".join(chr(34)+c+chr(34) for c in cols)} '
                f'FROM expert_records WHERE bucket = ?',
                (bucket,),
            ).fetchall()
            for row in data:
                key = tuple(row[c] if row[c] is not None else '' for c in cols)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({c: row[c] if row[c] is not None else '' for c in cols})
        finally:
            conn.close()
    return rows


def _collect_strong(paths):
    rows = []
    seen = set()
    for path in paths:
        if not os.path.isfile(path):
            continue
        conn = _connect(path, readonly=True)
        try:
            data = conn.execute(
                f'SELECT {",".join(chr(34)+c+chr(34) for c in STRONG_KEYS)} FROM strong_base_records'
            ).fetchall()
            for row in data:
                key = tuple(row[c] if row[c] is not None else '' for c in STRONG_KEYS)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({c: row[c] if row[c] is not None else '' for c in STRONG_KEYS})
        finally:
            conn.close()
    return rows


def _repair_db_file(province, main, expert_buckets, include_strong=False):
    if not os.path.isfile(main):
        return False
    paths = [main, db_part2_path(main), db_part3_path(main)]
    conn = _connect(main)
    try:
        _ensure_schema(conn, EXPERT_KEYS, STRONG_KEYS)
        meta_rows = conn.execute('SELECT * FROM dataset_meta').fetchall()
        metas = {row['batch_key']: dict(row) for row in meta_rows}
    finally:
        conn.close()

    bucket_records = {b: _collect_expert(paths, b) for b in expert_buckets}
    strong_rows = _collect_strong(paths) if include_strong else []

    for path in paths[1:]:
        if os.path.isfile(path):
            os.remove(path)

    conn = _connect(main)
    try:
        _ensure_schema(conn, EXPERT_KEYS, STRONG_KEYS)
        conn.execute('DELETE FROM expert_records')
        if include_strong:
            conn.execute('DELETE FROM strong_base_records')
        for bucket in expert_buckets:
            records = bucket_records[bucket]
            if not records:
                continue
            cols = ['bucket'] + EXPERT_KEYS
            ph = ','.join('?' * len(cols))
            sql = f'INSERT INTO expert_records ({",".join(chr(34)+c+chr(34) for c in cols)}) VALUES ({ph})'
            conn.executemany(
                sql,
                [[bucket] + [r.get(k, '') for k in EXPERT_KEYS] for r in records],
            )
            if bucket in metas:
                m = metas[bucket]
                _save_meta(conn, bucket, {
                    'id': m.get('dataset_id'),
                    'title': m.get('title'),
                    'dataset_type': m.get('dataset_type'),
                    'batch': m.get('batch_label'),
                    'province': m.get('province') or province,
                    'year': m.get('year'),
                    'count': len(records),
                    'columns': __import__('json').loads(m.get('columns_json') or '[]'),
                })
        if include_strong and strong_rows:
            ph = ','.join('?' * len(STRONG_KEYS))
            sql = f'INSERT INTO strong_base_records ({",".join(chr(34)+c+chr(34) for c in STRONG_KEYS)}) VALUES ({ph})'
            conn.executemany(sql, [[r.get(k, '') for k in STRONG_KEYS] for r in strong_rows])
            if STRONG_BUCKET in metas:
                m = metas[STRONG_BUCKET]
                _save_meta(conn, STRONG_BUCKET, {
                    'id': m.get('dataset_id'),
                    'title': m.get('title'),
                    'dataset_type': m.get('dataset_type'),
                    'batch': m.get('batch_label'),
                    'province': m.get('province') or province,
                    'year': m.get('year'),
                    'count': len(strong_rows),
                    'columns': __import__('json').loads(m.get('columns_json') or '[]'),
                })
        conn.commit()
    finally:
        conn.close()

    _vacuum(main)
    split_db_file_if_needed(province, main, EXPERT_KEYS, STRONG_KEYS)
    return True


def repair_province(province):
    ok = False
    if _repair_db_file(province, province_db_undergraduate(province), ('undergraduate',)):
        ok = True
    if _repair_db_file(province, province_db_other(province), ('early', 'junior'), include_strong=True):
        ok = True
    return ok


def main():
    targets = sys.argv[1:] or ['河南']
    for name in targets:
        if repair_province(name):
            print('repaired', name)
    rebuild_datasets_registry()
    return 0


if __name__ == '__main__':
    sys.exit(main())
