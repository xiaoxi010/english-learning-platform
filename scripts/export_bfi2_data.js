/**
 * 导出 BFI-2 题库到 data/
 * 用法: node scripts/export_bfi2_data.js
 */
const fs = require('fs');
const path = require('path');

const SRC_CANDIDATES = [
  path.join('C:', 'Users', 'HP', 'PycharmProjects', '临时文件', '测评题数据库', 'BFI-2 大五人格题目与计算方法.js'),
  path.join(__dirname, '..', '..', '..', 'Users', 'HP', 'PycharmProjects', '临时文件', '测评题数据库', 'BFI-2 大五人格题目与计算方法.js'),
];

function loadSrc() {
  const vm = require('vm');
  for (const p of SRC_CANDIDATES) {
    if (!fs.existsSync(p)) continue;
    let code = fs.readFileSync(p, 'utf8');
    const cut = code.indexOf('// 使用示例');
    if (cut >= 0) code = code.slice(0, cut);
    code = code.replace(/^const BFI2\s*=/m, 'var BFI2 =');
    const sandbox = { module: { exports: {} }, exports: {} };
    vm.runInNewContext(`${code}\nmodule.exports = BFI2;`, sandbox);
    const data = sandbox.module.exports;
    if (data && data.questions && data.questions.length) {
      return { data, path: p };
    }
  }
  throw new Error('找不到 BFI-2 大五人格题目与计算方法.js，请检查 scripts/export_bfi2_data.js 中的路径');
}

/** 与小程序 大五人格算法.js 五档常模结构一致（主维 12–60，面维 4–20） */
const NORMS = {
  mainDimensions: {
    veryLow: { max: 24, label: '很低' },
    low: { max: 32, label: '偏低' },
    medium: { max: 42, label: '中等' },
    high: { max: 52, label: '偏高' },
    veryHigh: { max: 60, label: '很高' },
  },
  facets: {
    veryLow: { max: 8, label: '很低' },
    low: { max: 11, label: '偏低' },
    medium: { max: 14, label: '中等' },
    high: { max: 17, label: '偏高' },
    veryHigh: { max: 20, label: '很高' },
  },
};

const MATCH_META = {
  teamRoles: [
    { key: 'leader', label: '领导者', intro: '擅长目标决策与推动落地，适合带领团队突破复杂任务。' },
    { key: 'executor', label: '执行者', intro: '踏实可靠、重视计划与交付，适合把战略拆解为可执行结果。' },
    { key: 'creator', label: '创意者', intro: '思维发散、善于提出新方案，适合创新类产品与内容岗位。' },
    { key: 'coordinator', label: '协调者', intro: '善于沟通整合资源，适合跨部门协同与项目管理型角色。' },
    { key: 'supporter', label: '支持者', intro: '亲和力强、关注团队氛围，适合培训、客服与协作支持类岗位。' },
    { key: 'critic', label: '批评者', intro: '善于质疑与质量控制，适合评审、风控与需要独立判断的角色。' },
  ],
  workEnvironments: [
    { key: 'innovative', label: '创新型环境', intro: '强调快速迭代与试错，适合互联网、科技与研发场景。' },
    { key: 'traditional', label: '传统型环境', intro: '强调制度与流程稳定，适合机关单位、银行与大型国企。' },
    { key: 'highPressure', label: '高压型环境', intro: '节奏快、任务密集，适合金融、医疗与应急管理等领域。' },
    { key: 'teamOriented', label: '团队型环境', intro: '强调协作与集体决策，适合人力、咨询与教育行业。' },
    { key: 'independent', label: '独立型环境', intro: '强调自主安排与深度工作，适合科研、编程与创作类岗位。' },
  ],
  careerTypes: [
    { key: 'management', label: '管理类职业', intro: '整合资源、带团队拿结果的中高层管理通道。' },
    { key: 'technical', label: '技术类职业', intro: '依赖专业深度与系统思维的技术路径。' },
    { key: 'service', label: '服务类职业', intro: '面向人际支持与用户体验的岗位体系。' },
    { key: 'creative', label: '创意类职业', intro: '内容、设计与创新产品相关的工作形态。' },
    { key: 'sales', label: '销售类职业', intro: '需要影响力、客户开拓与目标导向的岗位。' },
  ],
};

const { data: BFI2, path: srcPath } = loadSrc();
const questions = BFI2.questions.map((q) => {
  const item = { ...q };
  if (item.id === 60 && item.facet === 'aestheticSensitivity') {
    item.facet = 'creativeImagination';
  }
  return item;
});

const outDir = path.join(__dirname, '..', 'data');
const database = {
  info: BFI2.info,
  ratingScale: BFI2.ratingScale,
  questions,
  dimensions: BFI2.dimensions,
  norms: NORMS,
  matchMeta: MATCH_META,
};

function write(name, obj) {
  const p = path.join(outDir, name);
  fs.writeFileSync(p, JSON.stringify(obj, null, 2), 'utf8');
  console.log('wrote', p);
}

write('bfi2_questions.json', questions);
write('bfi2_rating_scale.json', BFI2.ratingScale);
write('bfi2_dimensions.json', BFI2.dimensions);
write('bfi2_norms.json', NORMS);
write('bfi2_match_meta.json', MATCH_META);
write('bfi2_meta.json', { ...BFI2.info, questionCount: 60, ratingLabels: BFI2.ratingScale });
write('bfi2_database.json', database);
console.log('source:', srcPath);
console.log('done', questions.length, 'questions');
