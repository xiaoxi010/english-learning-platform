吉林省 2025 招生计划 JSON
========================

文件：吉林省_2025招生计划.json
来源：桌面 2293391970.xlsx（吉林省普通高考分科类、分专业招生计划）

范围：
  - 吉林省_2025招生计划.json — 历史类、物理类（普通类）
  - 吉林省_2025招生计划_体育艺术类.json — 历史体育类、物理体育类、历史艺术类、物理艺术类

重新生成（普通类）：
  python jilin_2025_enrollment_loader.py general

重新生成（体育艺术类）：
  python jilin_2025_enrollment_loader.py sport_art

全部重新生成：
  python jilin_2025_enrollment_loader.py all

每条记录字段：
  - 大学
  - 专业
  - 批次：提前A / 提前B / 本科 / 专科
  - 类别：历史类 / 物理类
  - 学制
  - 招生人数
  - 再选选科要求：不限，或具体科目（如思想政治/化学）
  - 专业备注：原文备注

重新生成：
  python jilin_2025_enrollment_loader.py "源xlsx路径" "输出json路径"

默认输出：
  data/college_major_scores/吉林省_2025招生计划.json
