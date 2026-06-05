# 高考报考 · 多省数据

## 目录结构

```
data/gaokao_apply/
  provinces/
    吉林/
      manifest.json          # 导入元数据、各批次条数
      data.undergraduate.db   # 本科批
      data.other.db           # 提前批 / 专科批 / 强基
      data.*.part2.db         # 可选：单库超 95MB 时的第二分片
      source/
        expert.xlsx          # 专家版源文件（复制自桌面）
        strong_base.xlsx     # 强基源文件（如有）
    北京/
      ...
  jilin_2025_*.json          # 吉林省兼容旧路径（导入吉林后自动同步）
  school_reference.json      # 全国院校参考
```

## 桌面源数据

| 类型 | 默认目录 |
|------|----------|
| 专家版（29 省） | `Desktop\01-【正式数据】专家版2026\` |
| 强基计划 | `Desktop\03-【正式数据】其他数据2026\强基2025年计划分数线\` |

## 导入命令

```bash
# 查看桌面源文件与省份映射
python import_gaokao_provinces.py --list

# 导入全部省份（耗时较长，建议分批）
python import_gaokao_provinces.py

# 仅导入指定省
python import_gaokao_provinces.py 吉林 北京 山东

# 查看已导入状态
python import_gaokao_provinces.py --status

# 重建数据集注册表
python gaokao_jilin_data_loader.py rebuild

# 从旧 JSON 迁移为 data.db（一般只需运行一次）
python migrate_gaokao_json_to_db.py
```

## 数据集 ID

格式：`{slug}_2026_expert_undergraduate`（如 `beijing_2026_expert_undergraduate`）

吉林省同时保留别名：`jilin_2025_expert_undergraduate`

API 查询时传 `province=北京` 与 `dataset=undergraduate`（或 strong / early / junior）。

## 各省 Excel 格式

专家版各省列顺序不同，导入时**按表头中文**映射到与吉林省相同的 JSON 字段（见 `gaokao_expert_import.py`）。

- 标准模板：表头含「院校名称」「院校代码」等（多数省份）
- 山东模板：表头为「院校」「专业」「批次」等宽表
- 若省表含「计划类别」列，会写入 `plan_category` 字段

重新导入某省：

```bash
python import_gaokao_provinces.py 安徽
```
