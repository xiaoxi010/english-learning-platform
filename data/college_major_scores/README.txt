吉林省 2026 院校专业分数参考
================================

Excel 源文件：jilin_2026.xlsx
JSON 缓存：  jilin_2026.json

表头映射（Excel → 系统字段）
  生源地     → source_region
  必选科目   → required_subjects（Excel「批次」后一列：历史/物理，即科类）
  院校名称   → school_name
  专业名称   → major_name
  专业备注   → major_note
  最低分     → min_score
  最低位次   → min_rank
  最高分     → max_score
  最高位次   → max_rank

重新生成 JSON：
  python -c "from college_major_score_loader import build_dataset_json; build_dataset_json('jilin_2026')"
