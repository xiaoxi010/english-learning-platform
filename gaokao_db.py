# gaokao_db.py — 每省两个 SQLite：本科批 + 其余批次（各自可再拆 part2/part3）
"""路径：data/gaokao_apply/provinces/{省名}/data.undergraduate.db | data.other.db"""
import json
import os
import sqlite3

from gaokao_province_registry import norm_province, province_dir, read_manifest, write_manifest

UNDERGRADUATE_DB_NAME = 'data.undergraduate.db'
OTHER_DB_NAME = 'data.other.db'
LEGACY_DB_NAME = 'data.db'
EXPERT_BUCKETS = ('early', 'undergraduate', 'junior')
STRONG_BUCKET = 'strong'
OTHER_BATCH_KEYS = ('early', 'junior', STRONG_BUCKET)
MAX_DB_BYTES = 95 * 1024 * 1024


def province_db_undergraduate(province):
    return os.path.join(province_dir(province), UNDERGRADUATE_DB_NAME)


def province_db_other(province):
    return os.path.join(province_dir(province), OTHER_DB_NAME)


def province_db_path(province):
    """本科批数据库（兼容旧调用）。"""
    return province_db_undergraduate(province)


def province_db_for_batch(province, batch_key):
    if batch_key == 'undergraduate':
        return province_db_undergraduate(province)
    return province_db_other(province)


def legacy_province_db_path(province):
    return os.path.join(province_dir(province), LEGACY_DB_NAME)


def db_part2_path(db_path):
    base, ext = os.path.splitext(db_path)
    return f'{base}.part2{ext or ".db"}'


def db_part3_path(db_path):
    base, ext = os.path.splitext(db_path)
    return f'{base}.part3{ext or ".db"}'


def _norm_cell(val):
    if val is None:
        return ''
    if isinstance(val, float):
        if val != val:
            return ''
        if val == int(val):
            return str(int(val))
    return str(val)


def _connect(db_path, readonly=False):
    os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
    if readonly and os.path.isfile(db_path):
        uri = f'file:{db_path}?mode=ro'
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA busy_timeout=60000')
    return conn


def _checkpoint(db_path):
    if not os.path.isfile(db_path):
        return
    conn = _connect(db_path)
    try:
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        conn.commit()
    finally:
        conn.close()


def _db_size(path):
    return os.path.getsize(path) if os.path.isfile(path) else 0


def _ensure_schema(conn, expert_keys, strong_keys):
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS dataset_meta (
            batch_key TEXT PRIMARY KEY,
            dataset_id TEXT,
            dataset_type TEXT,
            batch_label TEXT,
            title TEXT,
            province TEXT,
            year INTEGER,
            record_count INTEGER,
            columns_json TEXT
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS db_info (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        '''
    )
    exp_cols = ', '.join(f'"{k}" TEXT' for k in expert_keys)
    conn.execute(
        f'''
        CREATE TABLE IF NOT EXISTS expert_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bucket TEXT NOT NULL,
            {exp_cols}
        )
        '''
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_expert_bucket ON expert_records(bucket)'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_expert_school ON expert_records(school_name)'
    )
    strong_cols = ', '.join(f'"{k}" TEXT' for k in strong_keys)
    conn.execute(
        f'''
        CREATE TABLE IF NOT EXISTS strong_base_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {strong_cols}
        )
        '''
    )
    conn.commit()


def _quoted_cols(cols):
    return ','.join(f'"{c}"' for c in cols)


def _db_part_paths(main_path):
    paths = [main_path]
    p2 = db_part2_path(main_path)
    p3 = db_part3_path(main_path)
    if os.path.isfile(p2):
        paths.append(p2)
    if os.path.isfile(p3):
        paths.append(p3)
    return paths


def _open_db_parts_by_path(main_path, readonly=False):
    if not os.path.isfile(main_path):
        return main_path, [], None
    paths = _db_part_paths(main_path)
    conns = [_connect(p, readonly=readonly) for p in paths]
    return main_path, paths, conns


def _open_db_parts(province, batch_key, readonly=False):
    main = province_db_for_batch(province, batch_key)
    return _open_db_parts_by_path(main, readonly=readonly)


def _close_conns(conns):
    if not conns:
        return
    if not isinstance(conns, (list, tuple)):
        conns = [conns]
    for conn in conns:
        if conn:
            conn.close()


def _expert_insert_cols(expert_keys):
    return ['bucket'] + list(expert_keys)


def _rows_to_records(rows, keys):
    records = []
    for row in rows:
        rec = {k: row[k] if row[k] is not None else '' for k in keys}
        records.append(rec)
    return records


def _fetch_expert_records(conns, bucket, expert_keys):
    keys = list(expert_keys)
    records = []
    sql = f'SELECT {_quoted_cols(keys)} FROM expert_records WHERE bucket = ? ORDER BY id'
    for conn in conns:
        if not conn:
            continue
        rows = conn.execute(sql, (bucket,)).fetchall()
        records.extend(_rows_to_records(rows, keys))
    return records


def _fetch_strong_records(conns, strong_keys):
    keys = list(strong_keys)
    records = []
    sql = f'SELECT {_quoted_cols(keys)} FROM strong_base_records ORDER BY id'
    for conn in conns:
        if not conn:
            continue
        rows = conn.execute(sql).fetchall()
        records.extend(_rows_to_records(rows, keys))
    return records


def _count_expert(conns, bucket):
    total = 0
    for conn in conns:
        if not conn:
            continue
        row = conn.execute(
            'SELECT COUNT(*) AS c FROM expert_records WHERE bucket = ?',
            (bucket,),
        ).fetchone()
        total += int(row['c'] or 0)
    return total


def _count_strong(conns):
    total = 0
    for conn in conns:
        if not conn:
            continue
        row = conn.execute('SELECT COUNT(*) AS c FROM strong_base_records').fetchone()
        total += int(row['c'] or 0)
    return total


def _legacy_db_exists(province):
    return os.path.isfile(legacy_province_db_path(province))


def province_has_db(province):
    return (
        os.path.isfile(province_db_undergraduate(province))
        or os.path.isfile(province_db_other(province))
        or _legacy_db_exists(province)
    )


def batch_exists(province, batch_key):
    if _legacy_db_exists(province) and not os.path.isfile(province_db_for_batch(province, batch_key)):
        _, _, conns = _open_db_parts_by_path(legacy_province_db_path(province), readonly=True)
    else:
        main = province_db_for_batch(province, batch_key)
        if not os.path.isfile(main):
            return False
        _, _, conns = _open_db_parts(province, batch_key, readonly=True)
    try:
        if not conns:
            return False
        conn1 = conns[0]
        row = conn1.execute(
            'SELECT record_count FROM dataset_meta WHERE batch_key = ?',
            (batch_key,),
        ).fetchone()
        if row and int(row['record_count'] or 0) > 0:
            return True
        if batch_key == STRONG_BUCKET:
            return _count_strong(conns) > 0
        return _count_expert(conns, batch_key) > 0
    finally:
        _close_conns(conns)


def dataset_count(province, batch_key):
    if not batch_exists(province, batch_key):
        return 0
    if _legacy_db_exists(province) and not os.path.isfile(province_db_for_batch(province, batch_key)):
        _, _, conns = _open_db_parts_by_path(legacy_province_db_path(province), readonly=True)
    else:
        _, _, conns = _open_db_parts(province, batch_key, readonly=True)
    try:
        conn1 = conns[0]
        row = conn1.execute(
            'SELECT record_count FROM dataset_meta WHERE batch_key = ?',
            (batch_key,),
        ).fetchone()
        if row and row['record_count'] is not None:
            return int(row['record_count'])
        if batch_key == STRONG_BUCKET:
            return _count_strong(conns)
        return _count_expert(conns, batch_key)
    finally:
        _close_conns(conns)


def _save_meta(conn, batch_key, meta):
    conn.execute(
        '''
        INSERT INTO dataset_meta (
            batch_key, dataset_id, dataset_type, batch_label, title,
            province, year, record_count, columns_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(batch_key) DO UPDATE SET
            dataset_id = excluded.dataset_id,
            dataset_type = excluded.dataset_type,
            batch_label = excluded.batch_label,
            title = excluded.title,
            province = excluded.province,
            year = excluded.year,
            record_count = excluded.record_count,
            columns_json = excluded.columns_json
        ''',
        (
            batch_key,
            meta.get('id') or '',
            meta.get('dataset_type') or '',
            meta.get('batch') or meta.get('batch_label') or '',
            meta.get('title') or '',
            meta.get('province') or '',
            int(meta.get('year') or 0),
            int(meta.get('count') or 0),
            json.dumps(meta.get('columns') or [], ensure_ascii=False),
        ),
    )


def _delete_expert_bucket(conns, bucket_key):
    for conn in conns:
        if conn:
            conn.execute('DELETE FROM expert_records WHERE bucket = ?', (bucket_key,))


def _delete_strong(conns):
    for conn in conns:
        if conn:
            conn.execute('DELETE FROM strong_base_records')


def _mark_split(province, main_path, part2_path):
    conn = _connect(main_path)
    try:
        conn.execute(
            'INSERT INTO db_info (key, value) VALUES (?, ?) '
            'ON CONFLICT(key) DO UPDATE SET value = excluded.value',
            ('split_parts', '2'),
        )
        conn.execute(
            'INSERT INTO db_info (key, value) VALUES (?, ?) '
            'ON CONFLICT(key) DO UPDATE SET value = excluded.value',
            ('part2_file', os.path.basename(part2_path)),
        )
        conn.commit()
    finally:
        conn.close()
    manifest = read_manifest(province) or {}
    key = 'db_undergraduate_part2' if main_path.endswith(UNDERGRADUATE_DB_NAME) else 'db_other_part2'
    write_manifest(province, {
        **manifest,
        'db_undergraduate': UNDERGRADUATE_DB_NAME,
        'db_other': OTHER_DB_NAME,
        key: os.path.basename(part2_path),
    })


def _clear_split_mark(province, main_path):
    part2 = db_part2_path(main_path)
    if os.path.isfile(part2):
        return
    if not os.path.isfile(main_path):
        return
    conn = _connect(main_path)
    try:
        conn.execute("DELETE FROM db_info WHERE key IN ('split_parts', 'part2_file')")
        conn.commit()
    finally:
        conn.close()
    manifest = read_manifest(province) or {}
    key = 'db_undergraduate_part2' if main_path.endswith(UNDERGRADUATE_DB_NAME) else 'db_other_part2'
    if key in manifest:
        manifest = dict(manifest)
        manifest.pop(key, None)
        write_manifest(province, manifest)


def _ensure_part2(main_conn, part2_path, expert_keys, strong_keys):
    if os.path.isfile(part2_path):
        return
    p2 = _connect(part2_path)
    try:
        _ensure_schema(p2, expert_keys, strong_keys)
        p2.commit()
    finally:
        p2.close()


def _move_expert_rows_between(main_conn, other_path, expert_keys, bucket, id_list, to_part2, p2_attached=False):
    if not id_list:
        return
    cols = _expert_insert_cols(expert_keys)
    col_sql = _quoted_cols(cols)
    data_cols = _quoted_cols(expert_keys)
    ph = ','.join('?' * len(id_list))
    src_conn = main_conn if to_part2 else _connect(other_path)
    dst_conn = _connect(other_path) if to_part2 else main_conn
    try:
        _ensure_schema(dst_conn, expert_keys, ('province', 'school_name', 'major_name', 'qualify_score', 'admit_score'))
        rows = src_conn.execute(
            f'SELECT {data_cols} FROM expert_records WHERE bucket = ? AND id IN ({ph})',
            [bucket, *id_list],
        ).fetchall()
        if not rows:
            return
        insert_sql = f'INSERT INTO expert_records ({col_sql}) VALUES ({",".join("?" * len(cols))})'
        dst_conn.executemany(
            insert_sql,
            [[bucket] + [r[c] for c in expert_keys] for r in rows],
        )
        src_conn.execute(
            f'DELETE FROM expert_records WHERE bucket = ? AND id IN ({ph})',
            [bucket, *id_list],
        )
        if to_part2:
            dst_conn.commit()
            main_conn.commit()
        else:
            main_conn.commit()
            if src_conn is not main_conn:
                src_conn.commit()
    finally:
        if not to_part2 and src_conn is not main_conn:
            src_conn.close()


def _move_strong_rows_between(main_conn, other_path, expert_keys, strong_keys, id_list, to_part2, p2_attached=False):
    if not id_list:
        return
    col_sql = _quoted_cols(strong_keys)
    ph = ','.join('?' * len(id_list))
    src_conn = main_conn if to_part2 else _connect(other_path)
    dst_conn = _connect(other_path) if to_part2 else main_conn
    try:
        _ensure_schema(dst_conn, expert_keys, strong_keys)
        rows = src_conn.execute(
            f'SELECT {col_sql} FROM strong_base_records WHERE id IN ({ph})',
            id_list,
        ).fetchall()
        if not rows:
            return
        insert_sql = f'INSERT INTO strong_base_records ({col_sql}) VALUES ({",".join("?" * len(strong_keys))})'
        dst_conn.executemany(insert_sql, [list(r) for r in rows])
        src_conn.execute(f'DELETE FROM strong_base_records WHERE id IN ({ph})', id_list)
        if to_part2:
            dst_conn.commit()
            main_conn.commit()
        else:
            main_conn.commit()
            if src_conn is not main_conn:
                src_conn.commit()
    finally:
        if not to_part2 and src_conn is not main_conn:
            src_conn.close()


def _split_largest_expert_half(main_conn, other_path, expert_keys, strong_keys, from_part2):
    if from_part2:
        main_conn.execute('ATTACH DATABASE ? AS p2', (other_path,))
    try:
        if from_part2:
            row = main_conn.execute(
                'SELECT bucket, COUNT(*) AS c FROM p2.expert_records '
                'GROUP BY bucket ORDER BY c DESC LIMIT 1'
            ).fetchone()
            if not row or int(row['c'] or 0) <= 1:
                return False
            bucket = row['bucket']
            ids = [
                int(r['id']) for r in main_conn.execute(
                    'SELECT id FROM p2.expert_records WHERE bucket = ? ORDER BY id',
                    (bucket,),
                ).fetchall()
            ]
        else:
            row = main_conn.execute(
                'SELECT bucket, COUNT(*) AS c FROM expert_records '
                'GROUP BY bucket ORDER BY c DESC LIMIT 1'
            ).fetchone()
            if not row or int(row['c'] or 0) <= 1:
                return False
            bucket = row['bucket']
            ids = [
                int(r['id']) for r in main_conn.execute(
                    'SELECT id FROM expert_records WHERE bucket = ? ORDER BY id',
                    (bucket,),
                ).fetchall()
            ]
        mid = len(ids) // 2
        if mid <= 0:
            return False
        move_ids = ids[mid:]
        _move_expert_rows_between(
            main_conn, other_path, expert_keys, bucket, move_ids,
            to_part2=not from_part2, p2_attached=from_part2,
        )
        return True
    finally:
        if from_part2:
            try:
                main_conn.execute('DETACH DATABASE p2')
            except sqlite3.OperationalError:
                pass


def _split_largest_strong_half(main_conn, other_path, expert_keys, strong_keys, from_part2):
    if from_part2:
        main_conn.execute('ATTACH DATABASE ? AS p2', (other_path,))
    try:
        src = 'p2.strong_base_records' if from_part2 else 'strong_base_records'
        row = main_conn.execute(f'SELECT COUNT(*) AS c FROM {src}').fetchone()
        if not row or int(row['c'] or 0) <= 1:
            return False
        ids = [
            int(r['id']) for r in main_conn.execute(
                f'SELECT id FROM {src} ORDER BY id'
            ).fetchall()
        ]
        mid = len(ids) // 2
        if mid <= 0:
            return False
        move_ids = ids[mid:]
        _move_strong_rows_between(
            main_conn, other_path, expert_keys, strong_keys, move_ids,
            to_part2=not from_part2, p2_attached=from_part2,
        )
        return True
    finally:
        if from_part2:
            try:
                main_conn.execute('DETACH DATABASE p2')
            except sqlite3.OperationalError:
                pass


def split_db_file_if_needed(province, main_path, expert_keys, strong_keys, max_bytes=MAX_DB_BYTES):
    """超限时拆分单个数据库文件（本科或其余批次）。"""
    province = norm_province(province)
    part2 = db_part2_path(main_path)
    if not os.path.isfile(main_path):
        return False

    _checkpoint(main_path)
    if os.path.isfile(part2):
        _checkpoint(part2)

    changed = False
    guard = 0
    while guard < 80:
        guard += 1
        main_s = _db_size(main_path)
        part2_s = _db_size(part2) if os.path.isfile(part2) else 0
        if main_s <= max_bytes and part2_s <= max_bytes:
            break

        conn = _connect(main_path)
        try:
            _ensure_schema(conn, expert_keys, strong_keys)
            moved = False
            if part2_s > max_bytes and (main_s <= max_bytes or part2_s >= main_s):
                if not os.path.isfile(part2):
                    break
                moved = _split_largest_expert_half(conn, part2, expert_keys, strong_keys, from_part2=True)
                if not moved:
                    moved = _split_largest_strong_half(
                        conn, part2, expert_keys, strong_keys, from_part2=True,
                    )
            elif main_s > max_bytes:
                if not os.path.isfile(part2):
                    _ensure_part2(conn, part2, expert_keys, strong_keys)
                moved = _split_largest_expert_half(conn, part2, expert_keys, strong_keys, from_part2=False)
                if not moved:
                    n = conn.execute('SELECT COUNT(*) AS c FROM strong_base_records').fetchone()
                    if int(n['c'] or 0) > 1:
                        moved = _split_largest_strong_half(
                            conn, part2, expert_keys, strong_keys, from_part2=False,
                        )
            if not moved:
                break
            conn.commit()
            changed = True
        finally:
            conn.close()
        _checkpoint(main_path)
        if os.path.isfile(part2):
            _checkpoint(part2)
        if guard % 3 == 0:
            _vacuum(main_path)
            if os.path.isfile(part2):
                _vacuum(part2)

    if os.path.isfile(part2) and _db_size(part2) > 0:
        _mark_split(province, main_path, part2)
        changed = True
    else:
        if os.path.isfile(part2) and _db_size(part2) == 0:
            os.remove(part2)
        _clear_split_mark(province, main_path)

    if changed:
        _vacuum(main_path)
        if os.path.isfile(part2):
            _vacuum(part2)

    git_limit = 100 * 1024 * 1024
    if _db_size(main_path) > git_limit or (os.path.isfile(part2) and _db_size(part2) > git_limit):
        if _balance_part3(province, main_path, expert_keys, strong_keys, git_limit):
            changed = True
    return changed


def split_db_if_needed(province, expert_keys, strong_keys, max_bytes=MAX_DB_BYTES):
    """拆分该省所有已存在的数据库文件。"""
    changed = False
    for main in (province_db_undergraduate(province), province_db_other(province)):
        if os.path.isfile(main):
            if split_db_file_if_needed(province, main, expert_keys, strong_keys, max_bytes):
                changed = True
    return changed


def _balance_part3(province, main, expert_keys, strong_keys, max_bytes):
    part2 = db_part2_path(main)
    part3 = db_part3_path(main)
    changed = False
    for _ in range(24):
        _checkpoint(main)
        if os.path.isfile(part2):
            _checkpoint(part2)
        if os.path.isfile(part3):
            _checkpoint(part3)
        sizes = [(main, _db_size(main))]
        if os.path.isfile(part2):
            sizes.append((part2, _db_size(part2)))
        if os.path.isfile(part3):
            sizes.append((part3, _db_size(part3)))
        if all(sz <= max_bytes for _, sz in sizes):
            break
        oversized = [(p, sz) for p, sz in sizes if sz > max_bytes]
        if not oversized:
            break
        src_path = max(oversized, key=lambda x: x[1])[0]
        if not os.path.isfile(part3):
            p3 = _connect(part3)
            try:
                _ensure_schema(p3, expert_keys, strong_keys)
                p3.commit()
            finally:
                p3.close()
        conn = _connect(main)
        try:
            _ensure_schema(conn, expert_keys, strong_keys)
            moved = False
            if src_path == main:
                moved = _split_largest_expert_half(conn, part3, expert_keys, strong_keys, from_part2=False)
                if not moved:
                    moved = _split_largest_strong_half(conn, part3, expert_keys, strong_keys, from_part2=False)
            elif src_path == part2:
                conn.execute('ATTACH DATABASE ? AS srcdb', (part2,))
                try:
                    row = conn.execute(
                        'SELECT bucket, COUNT(*) AS c FROM srcdb.expert_records '
                        'GROUP BY bucket ORDER BY c DESC LIMIT 1'
                    ).fetchone()
                    if row and int(row['c'] or 0) > 1:
                        bucket = row['bucket']
                        ids = [int(r['id']) for r in conn.execute(
                            'SELECT id FROM srcdb.expert_records WHERE bucket = ? ORDER BY id',
                            (bucket,),
                        ).fetchall()]
                        mid = len(ids) // 2
                        move_ids = ids[mid:]
                        conn.execute('ATTACH DATABASE ? AS p3db', (part3,))
                        try:
                            cols = _expert_insert_cols(expert_keys)
                            col_sql = _quoted_cols(cols)
                            ph = ','.join('?' * len(move_ids))
                            conn.execute(
                                f'INSERT INTO p3db.expert_records ({col_sql}) '
                                f'SELECT {col_sql} FROM srcdb.expert_records '
                                f'WHERE bucket = ? AND id IN ({ph})',
                                [bucket, *move_ids],
                            )
                            conn.execute(
                                f'DELETE FROM srcdb.expert_records WHERE bucket = ? AND id IN ({ph})',
                                [bucket, *move_ids],
                            )
                            moved = True
                        finally:
                            conn.execute('DETACH DATABASE p3db')
                finally:
                    conn.execute('DETACH DATABASE srcdb')
            if not moved:
                break
            conn.commit()
            changed = True
        finally:
            conn.close()
        if _ % 2 == 1:
            _vacuum(main)
            if os.path.isfile(part2):
                _vacuum(part2)
            if os.path.isfile(part3):
                _vacuum(part3)
    if os.path.isfile(part3) and _db_size(part3) > 0:
        manifest = read_manifest(province) or {}
        key = 'db_undergraduate_part3' if main.endswith(UNDERGRADUATE_DB_NAME) else 'db_other_part3'
        write_manifest(province, {**manifest, key: os.path.basename(part3)})
    return changed


def _vacuum(path):
    if not os.path.isfile(path):
        return
    conn = _connect(path)
    try:
        conn.execute('VACUUM')
        conn.commit()
    finally:
        conn.close()
    for suffix in ('-wal', '-shm'):
        side = path + suffix
        if os.path.isfile(side) and os.path.getsize(side) == 0:
            try:
                os.remove(side)
            except OSError:
                pass


def _write_to_db(main_path, province, batch_key, records, meta, expert_keys, strong_keys):
    _, _, conns = _open_db_parts_by_path(main_path)
    try:
        if not conns:
            conns = [_connect(main_path)]
        _ensure_schema(conns[0], expert_keys, strong_keys)
        for extra in conns[1:]:
            _ensure_schema(extra, expert_keys, strong_keys)
        if batch_key == STRONG_BUCKET:
            _delete_strong(conns)
            if records:
                cols = list(strong_keys)
                placeholders = ','.join('?' * len(cols))
                sql = f'INSERT INTO strong_base_records ({_quoted_cols(cols)}) VALUES ({placeholders})'
                rows = [[_norm_cell(rec.get(k)) for k in strong_keys] for rec in records]
                conns[0].executemany(sql, rows)
            meta = dict(meta)
            meta['count'] = len(records)
            meta['dataset_type'] = 'strong_base'
            _save_meta(conns[0], STRONG_BUCKET, meta)
        else:
            _delete_expert_bucket(conns, batch_key)
            if records:
                cols = _expert_insert_cols(expert_keys)
                placeholders = ','.join('?' * len(cols))
                sql = f'INSERT INTO expert_records ({_quoted_cols(cols)}) VALUES ({placeholders})'
                rows = [
                    [batch_key] + [_norm_cell(rec.get(k)) for k in expert_keys]
                    for rec in records
                ]
                conns[0].executemany(sql, rows)
            meta = dict(meta)
            meta['count'] = len(records)
            meta['dataset_type'] = 'expert'
            _save_meta(conns[0], batch_key, meta)
        for conn in conns:
            conn.commit()
    finally:
        _close_conns(conns)
    split_db_file_if_needed(province, main_path, expert_keys, strong_keys)
    return meta


def write_expert_bucket(province, bucket_key, records, meta, expert_keys, strong_keys=None):
    province = norm_province(province)
    strong_keys = strong_keys or ('province', 'school_name', 'major_name', 'qualify_score', 'admit_score')
    main_path = province_db_for_batch(province, bucket_key)
    os.makedirs(province_dir(province), exist_ok=True)
    return _write_to_db(main_path, province, bucket_key, records, meta, expert_keys, strong_keys)


def write_strong_base(province, records, meta, strong_keys, expert_keys=None):
    province = norm_province(province)
    expert_keys = expert_keys or ('school_name',)
    main_path = province_db_other(province)
    os.makedirs(province_dir(province), exist_ok=True)
    return _write_to_db(main_path, province, STRONG_BUCKET, records, meta, expert_keys, strong_keys)


def _read_meta(conn, batch_key):
    return conn.execute(
        'SELECT * FROM dataset_meta WHERE batch_key = ?',
        (batch_key,),
    ).fetchone()


def _build_payload(meta_row, records):
    columns = []
    try:
        columns = json.loads(meta_row['columns_json'] or '[]')
    except json.JSONDecodeError:
        columns = []
    return {
        'id': meta_row['dataset_id'],
        'title': meta_row['title'],
        'dataset_type': meta_row['dataset_type'],
        'batch': meta_row['batch_label'],
        'province': meta_row['province'],
        'year': meta_row['year'],
        'count': meta_row['record_count'],
        'columns': columns,
        'records': records,
    }


def read_dataset(province, batch_key, expert_keys, strong_keys):
    if batch_key == 'undergraduate':
        main = province_db_undergraduate(province)
    else:
        main = province_db_other(province)
    if not os.path.isfile(main):
        if _legacy_db_exists(province):
            main = legacy_province_db_path(province)
        else:
            return None
    return read_dataset_by_path(main, batch_key, 'strong_base' if batch_key == STRONG_BUCKET else 'expert', expert_keys, strong_keys)


def read_dataset_by_path(db_path, batch_key, dataset_type, expert_keys, strong_keys):
    if not os.path.isfile(db_path):
        return None
    _, _, conns = _open_db_parts_by_path(db_path, readonly=True)
    try:
        if not conns:
            return None
        bk = STRONG_BUCKET if dataset_type == 'strong_base' else batch_key
        meta_row = _read_meta(conns[0], bk if dataset_type != 'strong_base' else STRONG_BUCKET)
        if not meta_row and dataset_type == 'strong_base':
            meta_row = _read_meta(conns[0], STRONG_BUCKET)
        if not meta_row:
            return None
        if bk == STRONG_BUCKET:
            records = _fetch_strong_records(conns, strong_keys)
        else:
            records = _fetch_expert_records(conns, bk, expert_keys)
        payload = _build_payload(meta_row, records)
        payload['count'] = len(records)
        return payload
    finally:
        _close_conns(conns)


def _collect_expert_from_paths(paths, bucket, expert_keys):
    rows = []
    seen = set()
    cols = list(expert_keys)
    for path in paths:
        if not os.path.isfile(path):
            continue
        _, _, conns = _open_db_parts_by_path(path, readonly=True)
        try:
            for rec in _fetch_expert_records(conns, bucket, expert_keys):
                key = tuple(rec.get(c) or '' for c in cols)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(rec)
        finally:
            _close_conns(conns)
    return rows


def _collect_strong_from_paths(paths, strong_keys):
    rows = []
    seen = set()
    cols = list(strong_keys)
    for path in paths:
        if not os.path.isfile(path):
            continue
        _, _, conns = _open_db_parts_by_path(path, readonly=True)
        try:
            for rec in _fetch_strong_records(conns, strong_keys):
                key = tuple(rec.get(c) or '' for c in cols)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(rec)
        finally:
            _close_conns(conns)
    return rows


def _read_meta_from_paths(paths):
    metas = {}
    for path in paths:
        if not os.path.isfile(path):
            continue
        conn = _connect(path, readonly=True)
        try:
            for row in conn.execute('SELECT * FROM dataset_meta').fetchall():
                metas[row['batch_key']] = dict(row)
        finally:
            conn.close()
    return metas


def _legacy_part_paths(province):
    main = legacy_province_db_path(province)
    if not os.path.isfile(main):
        return []
    paths = [main]
    for extra in (db_part2_path(main), db_part3_path(main)):
        if os.path.isfile(extra):
            paths.append(extra)
    return paths


def _remove_db_files(*paths):
    for path in paths:
        if not path:
            continue
        for suffix in ('', '-wal', '-shm'):
            p = path + suffix if suffix else path
            if os.path.isfile(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


def migrate_province_to_batch_dbs(province, expert_keys, strong_keys):
    """将旧版 data.db（含 part2/part3）迁移为本科/其余两个库。"""
    province = norm_province(province)
    ug_path = province_db_undergraduate(province)
    other_path = province_db_other(province)
    legacy_paths = _legacy_part_paths(province)
    if not legacy_paths:
        return False

    metas = _read_meta_from_paths(legacy_paths)
    ug_records = _collect_expert_from_paths(legacy_paths, 'undergraduate', expert_keys)
    early_records = _collect_expert_from_paths(legacy_paths, 'early', expert_keys)
    junior_records = _collect_expert_from_paths(legacy_paths, 'junior', expert_keys)
    strong_records = _collect_strong_from_paths(legacy_paths, strong_keys)

    if ug_records:
        m = metas.get('undergraduate') or {}
        _write_to_db(ug_path, province, 'undergraduate', ug_records, {
            'id': m.get('dataset_id'),
            'title': m.get('title'),
            'dataset_type': 'expert',
            'batch': m.get('batch_label'),
            'province': m.get('province') or province,
            'year': m.get('year'),
            'count': len(ug_records),
            'columns': json.loads(m.get('columns_json') or '[]'),
        }, expert_keys, strong_keys)

    for bucket_key, records in (('early', early_records), ('junior', junior_records)):
        if not records:
            continue
        m = metas.get(bucket_key) or {}
        _write_to_db(other_path, province, bucket_key, records, {
            'id': m.get('dataset_id'),
            'title': m.get('title'),
            'dataset_type': 'expert',
            'batch': m.get('batch_label'),
            'province': m.get('province') or province,
            'year': m.get('year'),
            'count': len(records),
            'columns': json.loads(m.get('columns_json') or '[]'),
        }, expert_keys, strong_keys)

    if strong_records:
        m = metas.get(STRONG_BUCKET) or {}
        _write_to_db(other_path, province, STRONG_BUCKET, strong_records, {
            'id': m.get('dataset_id'),
            'title': m.get('title'),
            'dataset_type': 'strong_base',
            'batch': m.get('batch_label'),
            'province': m.get('province') or province,
            'year': m.get('year'),
            'count': len(strong_records),
            'columns': json.loads(m.get('columns_json') or '[]'),
        }, expert_keys, strong_keys)

    for path in legacy_paths:
        _remove_db_files(path)
        _remove_db_files(db_part2_path(path))
        _remove_db_files(db_part3_path(path))

    manifest = read_manifest(province) or {}
    manifest = dict(manifest)
    manifest.update({
        'storage': 'sqlite',
        'db_undergraduate': UNDERGRADUATE_DB_NAME,
        'db_other': OTHER_DB_NAME,
        'db_file': UNDERGRADUATE_DB_NAME,
    })
    manifest.pop('db_part2', None)
    manifest.pop('db_part3', None)
    write_manifest(province, manifest)
    return True


def migrate_json_payload_to_db(province, batch_key, payload, expert_keys, strong_keys):
    meta = {
        'id': payload.get('id'),
        'title': payload.get('title'),
        'dataset_type': payload.get('dataset_type'),
        'batch': payload.get('batch'),
        'province': payload.get('province') or norm_province(province),
        'year': payload.get('year'),
        'count': payload.get('count'),
        'columns': payload.get('columns'),
    }
    records = payload.get('records') or []
    if batch_key == STRONG_BUCKET or meta.get('dataset_type') == 'strong_base':
        return write_strong_base(
            province, records, meta, strong_keys,
            expert_keys=list(expert_keys),
        )
    return write_expert_bucket(
        province, batch_key, records, meta, expert_keys,
        strong_keys=list(strong_keys),
    )
