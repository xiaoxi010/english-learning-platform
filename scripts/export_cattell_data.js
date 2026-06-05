/**
 * 从小程序数据库导出卡特尔 16PF JSON 到 data/
 * 用法: node scripts/export_cattell_data.js
 */
const fs = require('fs');
const path = require('path');

const MP_UTILS = path.resolve(
  __dirname,
  '..',
  '..',
  '..',
  'Users',
  'HP',
  'Desktop',
  '吉致生涯',
  '吉致生涯',
  'life_code',
  'miniprogram',
  'utils'
);
const ALT_MP = 'C:\\Users\\HP\\Desktop\\吉致生涯\\吉致生涯\\life_code\\miniprogram\\utils';

function resolveUtils() {
  if (fs.existsSync(path.join(MP_UTILS, '卡特尔16种人格因素测评数据库.js'))) return MP_UTILS;
  if (fs.existsSync(path.join(ALT_MP, '卡特尔16种人格因素测评数据库.js'))) return ALT_MP;
  throw new Error('找不到小程序 utils 目录，请修改 scripts/export_cattell_data.js 中的路径');
}

const utilsDir = resolveUtils();
const db = require(path.join(utilsDir, '卡特尔16种人格因素测评数据库.js'));
const pf = require(path.join(utilsDir, '16PF.js'));

const outDir = path.join(__dirname, '..', 'data');

const questions = db.CATTEL16PF_QUESTIONS.map((q) => ({
  id: q.id,
  title: q.title,
  optionA: (q.optionA || '').replace(/^[ABC]\.\s*/, ''),
  optionB: (q.optionB || '').replace(/^[ABC]\.\s*/, ''),
  optionC: (q.optionC || '').replace(/^[ABC]\.\s*/, ''),
  isScored: q.isScored !== false,
}));

const secondary = db.CATTEL16PF_SECONDARY_FACTORS.map((f) => ({
  id: f.id,
  name: f.name,
  lowScore: f.lowScore,
  highScore: f.highScore,
  lowDesc: f.lowDesc,
  highDesc: f.highDesc,
}));

const dimensions = db.CATTEL16PF_DIMENSIONS.map((d) => ({
  id: d.id,
  name: d.name,
  lowScore: d.lowScore,
  highScore: d.highScore,
  lowDesc: d.lowDesc,
  highDesc: d.highDesc,
  suitableCareers: d.suitableCareers,
}));

const careers = pf.CATTEL16PF_CAREER_POOL;

const meta = {
  name: '卡特尔 16PF 人格因素测评',
  questionCount: 187,
  scoredCount: 185,
};

function write(name, obj) {
  const p = path.join(outDir, name);
  fs.writeFileSync(p, JSON.stringify(obj, null, 2), 'utf8');
  console.log('wrote', p, Array.isArray(obj) ? obj.length + ' items' : 'ok');
}

write('cattell_questions.json', questions);
write('cattell_scoring.json', db.CATTEL16PF_SCORING);
write('cattell_norms.json', db.CATTEL16PF_STANDARD_NORMS);
write('cattell_dimensions.json', dimensions);
write('cattell_secondary.json', secondary);
write('cattell_careers.json', careers);
write('cattell_meta.json', meta);
console.log('done');
