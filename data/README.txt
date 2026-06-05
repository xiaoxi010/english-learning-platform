数字天赋解读 / 生命密码文案库（已可从 Personality.js 导出）：

  e:\vxcode数据文件\data\Personality.json

获取方式（任选其一）：
1. 将 Personality.js 放到任意路径后执行：
   node scripts/export_personality_data.js "你的路径/Personality.js"
   （默认也会读取微信文件目录下的 Personality.js）
2. 微信云开发 → 数据库 personality_static → main，或云存储 Personality.json
3. 程序自动尝试：data/Personality.json、data/Personality.js、微信 2026-05 目录下的 Personality.js

文件需包含 Positively、MissingRepeated、Digital_union_code 等字段（与小程序一致）。

---

人生道路解读（已可从 lifeway.js 导出）：

  e:\vxcode数据文件\data\lifeway.json

获取方式（任选其一）：
1. 将 lifeway.js 放到任意路径后执行：
   node scripts/export_lifeway_data.js "你的路径/lifeway.js"
   （默认也会读取微信 2026-05 目录下的 lifeway.js）
2. 云数据库 lifeway_static → main，或云存储 lifeway.json
3. 程序自动尝试：data/lifeway.json、data/lifeway.js、微信目录 lifeway.js

需含 person_year_word 等字段（与小程序一致）。

---

学科能力测评请放置：

  e:\vxcode数据文件\data\subjectAbilityData.json

可从小程序目录复制：
  ...\life_code\miniprogram\data\subjectAbilityData.json

可选（推荐选科）：
  e:\vxcode数据文件\data\comprehensive.json
  或 综合能力评级.json（云存储「学科2.0/综合能力评级.json」）

---

霍兰德职业兴趣测评（已导出到本目录，一般无需再操作）：

  holland_questions.json      — 90 道题目
  holland_dimensions.json     — 六维解读文案
  holland_triple_careers.json — 120 组三维职业匹配
  holland_code_priority.json  — 三维码优先级表

---

艾克森情绪稳定性测评（已导出到本目录）：

  eysenck_questions.json   — 210 道题目
  eysenck_scoring.json     — 计分规则
  eysenck_dimensions.json  — 七维解读
  eysenck_patterns.json    — 情绪模式库
  eysenck_meta.json        — 测评元数据

计分与报告由 Python 模块 eysenck_calc.py / eysenck_report_vm.py 完成（无需 Node）。

---

星血趣味测评（星座 × 血型，已配置）：

  e:\vxcode数据文件\data\constellation.json

获取方式（任选其一）：
1. 将云存储下载的 constellation.json 复制到 data/，或执行：
   node scripts/export_constellation_data.js "你的路径/constellation.json"
   （默认也会读取微信 2026-05 目录下的 constellation.json）
2. 云开发云存储 / 数据库 constellation_static → main
3. 程序自动尝试：data/constellation.json、微信目录 constellation.json
