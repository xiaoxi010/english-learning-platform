/**
 * 导出 MBTI 趣味测评 48 题 + 类型解读数据
 * 用法: node scripts/export_mbti_data.js
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

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
const QUESTIONS_JS = path.join(MP_UTILS, 'MBTI趣味测评题目.js');
const MBTI_JS = path.join(MP_UTILS, 'MBTI.js');
const OUT = path.join(__dirname, '..', 'data');

function loadQuestions() {
  delete require.cache[require.resolve(QUESTIONS_JS)];
  const mod = require(QUESTIONS_JS);
  return mod.MBTI_FUN_QUIZ_QUESTIONS;
}

function loadMbtiMeta() {
  let code = fs.readFileSync(MBTI_JS, 'utf8');
  const cut = code.indexOf('module.exports');
  if (cut >= 0) code = code.slice(0, cut);
  code = code.replace(/^const MBTIData\s*=/m, 'var MBTIData =');
  const sandbox = { module: { exports: {} } };
  vm.runInNewContext(`${code}\nmodule.exports = MBTIData;`, sandbox);
  const d = sandbox.module.exports;
  const keys = [
    'total_word',
    'another_name',
    'point_word',
    'personal_feature',
    'personal_blind_spot',
    'job_advantage',
    'job_disadvantage',
    'post_characteristic',
    'fit_career',
    'fit_environment',
    'development_suggestion',
    'E',
    'I',
    'S',
    'N',
    'T',
    'F',
    'J',
    'P',
  ];
  const meta = {};
  keys.forEach((k) => {
    if (d[k] != null) meta[k] = d[k];
  });
  return meta;
}

const questions = loadQuestions();
const meta = loadMbtiMeta();

const likert = [
  { value: '-2', label: '完全不同意' },
  { value: '-1', label: '不同意' },
  { value: '0', label: '中立' },
  { value: '1', label: '同意' },
  { value: '2', label: '完全同意' },
];

fs.writeFileSync(path.join(OUT, 'mbti_questions.json'), JSON.stringify(questions, null, 2), 'utf8');
fs.writeFileSync(path.join(OUT, 'mbti_likert.json'), JSON.stringify(likert, null, 2), 'utf8');
fs.writeFileSync(path.join(OUT, 'mbti_types.json'), JSON.stringify(meta, null, 2), 'utf8');
fs.writeFileSync(
  path.join(OUT, 'mbti_meta.json'),
  JSON.stringify({ name: 'MBTI 趣味测评', questionCount: 48, mode: 'precise_48' }, null, 2),
  'utf8'
);
console.log('wrote', questions.length, 'questions + mbti_types.json');
