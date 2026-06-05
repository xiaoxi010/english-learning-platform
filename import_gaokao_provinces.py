#!/usr/bin/env python3
# import_gaokao_provinces.py — 从桌面正式数据导入各省专家版 / 强基 JSON
"""用法:
  python import_gaokao_provinces.py              # 导入全部已发现省份
  python import_gaokao_provinces.py 吉林 北京    # 仅导入指定省
  python import_gaokao_provinces.py --list       # 查看桌面源文件映射
"""
import argparse
import sys
from datetime import datetime

from gaokao_province_registry import (
    DESKTOP_EXPERT_DIR,
    DESKTOP_STRONG_DIR,
    discover_expert_files,
    discover_strong_base_files,
    list_imported_provinces,
    norm_province,
)
from gaokao_jilin_data_loader import (
    build_expert_json_for_province,
    build_strong_base_json_for_province,
    rebuild_datasets_registry,
    sync_jilin_legacy_json,
)


def import_one(province, expert_path=None, strong_path=None):
    province = norm_province(province)
    result = {'province': province, 'expert': None, 'strong': None, 'errors': []}
    if expert_path:
        try:
            result['expert'] = build_expert_json_for_province(
                province,
                xlsx_path=expert_path,
                copy_source=True,
            )
        except Exception as exc:
            result['errors'].append(f'expert: {exc}')
    if strong_path:
        try:
            result['strong'] = build_strong_base_json_for_province(
                province,
                xlsx_path=strong_path,
                copy_source=True,
            )
        except Exception as exc:
            result['errors'].append(f'strong: {exc}')
    if province == '吉林':
        try:
            sync_jilin_legacy_json(province)
        except Exception as exc:
            result['errors'].append(f'legacy: {exc}')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='导入各省高考专家版 / 强基数据')
    parser.add_argument('provinces', nargs='*', help='省名，省略则导入全部')
    parser.add_argument('--list', action='store_true', help='列出桌面源文件映射')
    parser.add_argument('--status', action='store_true', help='列出已导入省份')
    args = parser.parse_args(argv)

    expert_map = discover_expert_files()
    strong_map = discover_strong_base_files()

    if args.list:
        print('专家版目录:', DESKTOP_EXPERT_DIR)
        for prov in sorted(expert_map.keys()):
            print(f'  {prov}\t{expert_map[prov]}')
        print('\n强基目录:', DESKTOP_STRONG_DIR)
        for prov in sorted(strong_map.keys()):
            print(f'  {prov}\t{strong_map[prov]}')
        return 0

    if args.status:
        for row in list_imported_provinces():
            print(row['province'], 'expert' if row['has_expert'] else '-', 'strong' if row['has_strong'] else '-')
        return 0

    targets = [norm_province(p) for p in args.provinces] if args.provinces else sorted(expert_map.keys())
    if not targets:
        print('未在桌面专家版目录发现 Excel 文件', file=sys.stderr)
        return 1

    ok = 0
    fail = 0
    started = datetime.now().isoformat(timespec='seconds')
    print('开始导入', len(targets), '个省份', started)
    for prov in targets:
        expert_path = expert_map.get(prov)
        strong_path = strong_map.get(prov)
        if not expert_path and not strong_path:
            print(f'[跳过] {prov}: 未找到源文件')
            continue
        print(f'[导入] {prov} ...', flush=True)
        res = import_one(prov, expert_path, strong_path)
        if res['errors']:
            fail += 1
            print(f'  失败: {"; ".join(res["errors"])}')
        else:
            ok += 1
            ec = (res['expert'] or {}).get('counts') if isinstance(res['expert'], dict) else None
            sc = (res['strong'] or {}).get('count') if isinstance(res['strong'], dict) else None
            if ec:
                print(f'  专家版 early={ec.get("early", 0)} undergrad={ec.get("undergraduate", 0)} junior={ec.get("junior", 0)}')
            if sc is not None:
                print(f'  强基 {sc} 条')

    rebuild_datasets_registry()
    print(f'完成: 成功 {ok}, 失败 {fail}, 数据集 {len(rebuild_datasets_registry())} 个')
    return 0 if fail == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
