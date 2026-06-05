/**
 * 导出菲尔人格测评题目、计分表、结果区间
 * 用法: node scripts/export_feier_data.js
 */
const fs = require('fs');
const path = require('path');

const MP_UTILS = path.join(
  'C:',
  'Users',
  'HP',
  'Desktop',
  '吉致生涯',
  '吉致生涯',
  'life_code',
  'miniprogram',
  'utils'
);
const OUT = path.join(__dirname, '..', 'data');

function req(name) {
  const p = path.join(MP_UTILS, name);
  delete require.cache[require.resolve(p)];
  return require(p);
}

const mod = req('菲尔人格测评数据库.js');
const { FEIER_QUESTIONS, FEIER_SCORE_TABLE, FEIER_RESULT_BANDS } = mod;

const bands = FEIER_RESULT_BANDS.map((b) => ({
  key: b.key,
  min: b.min,
  max: b.max,
  title: b.title,
  subtitle: b.subtitle,
  analysis: b.analysis,
  careerHint: b.careerHint,
}));

fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'feier_questions.json'), JSON.stringify(FEIER_QUESTIONS, null, 2), 'utf8');
fs.writeFileSync(path.join(OUT, 'feier_score_table.json'), JSON.stringify(FEIER_SCORE_TABLE, null, 2), 'utf8');
fs.writeFileSync(path.join(OUT, 'feier_results.json'), JSON.stringify(bands, null, 2), 'utf8');
fs.writeFileSync(
  path.join(OUT, 'feier_meta.json'),
  JSON.stringify(
    {
      name: '菲尔人格测评',
      questionCount: FEIER_QUESTIONS.length,
      intro:
        '本测评源自美国著名心理学家菲尔・麦格劳（Phil McGraw）博士的经典人格理论，是全球流传最广的简易人格测评工具之一。通过日常习惯与下意识行为反应，剖析核心性格特质、处事逻辑和人际相处模式。',
      disclaimer:
        '本测评仅供个人娱乐和自我探索参考，不构成专业心理诊断、职业指导或任何形式的决策建议。',
    },
    null,
    2
  ),
  'utf8'
);

console.log('wrote', FEIER_QUESTIONS.length, 'questions + score table +', bands.length, 'result bands');
