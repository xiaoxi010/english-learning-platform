/**
 * 导出 RBTI 题目、人格文案、十二维解读
 * 用法: node scripts/export_rbti_data.js
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

const { QUESTIONS } = req('RBTIlogic.js');
const { PERSONALITY_TEXTS } = req('RBTIlabel.js');
const { DIMENSION_TEXTS } = req('RBTIDim_mean.js');

const questions = QUESTIONS.map((q) => ({
  id: q.id,
  title: q.title,
  optionA: q.optionA,
  optionB: q.optionB,
  optionC: q.optionC,
  optionD: q.optionD,
}));

fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'rbti_questions.json'), JSON.stringify(questions, null, 2), 'utf8');
fs.writeFileSync(
  path.join(OUT, 'rbti_personalities.json'),
  JSON.stringify(PERSONALITY_TEXTS, null, 2),
  'utf8'
);
fs.writeFileSync(
  path.join(OUT, 'rbti_dimensions.json'),
  JSON.stringify(DIMENSION_TEXTS, null, 2),
  'utf8'
);
fs.writeFileSync(
  path.join(OUT, 'rbti_meta.json'),
  JSON.stringify(
    {
      name: 'RBTI 年度抽象人格测评',
      questionCount: questions.length,
      axes: [
        { key: 'R', label: '荒谬', clusters: ['C1', 'C7', 'C11'] },
        { key: 'B', label: '较真', clusters: ['C2', 'C6', 'C9'] },
        { key: 'T', label: '搞心态', clusters: ['C3', 'C8', 'C10'] },
        { key: 'I', label: '摆烂', clusters: ['C4', 'C5', 'C12'] },
      ],
      about:
        'RBTI（Really Balanced Type Indicator，纯属虚构）是一套年度抽象人格测评，通过 31 道情境题统计你在「荒谬 / 较真 / 搞心态 / 摆烂」四条主轴上的倾向，并细分为 12 个维度。结果仅供娱乐，不构成任何心理诊断或职业建议。',
    },
    null,
    2
  ),
  'utf8'
);

console.log('wrote', questions.length, 'questions + personalities + dimensions');
