/**
 * 将 Personality.js（数字天赋 / 生命密码文案库）导出为 data/Personality.json
 * 用法:
 *   node scripts/export_personality_data.js
 *   node scripts/export_personality_data.js "路径/Personality.js"
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const OUT = path.join(__dirname, '..', 'data');
const DEFAULT_SRC = path.join(
  'e:',
  'xwechat_files',
  'wxid_6kz7tqac90kx22_67a2',
  'msg',
  'file',
  '2026-05',
  'Personality.js'
);

const CANDIDATES = [
  process.argv[2],
  process.env.PERSONALITY_SRC,
  DEFAULT_SRC,
  path.join(OUT, 'Personality.js'),
  path.join(OUT, 'Personality_source.js'),
].filter(Boolean);

function loadPersonalityJs(filePath) {
  let code = fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '');
  code = code.replace(/export\s+default\s+personalityData\s*;?\s*$/i, '').trim();
  if (!/personalityData\s*=/.test(code)) {
    throw new Error('未找到 personalityData 对象');
  }
  const sandbox = { module: { exports: {} } };
  vm.runInNewContext(`${code}\nmodule.exports = personalityData;`, sandbox);
  const data = sandbox.module.exports;
  if (!data || typeof data !== 'object' || !data.Positively) {
    throw new Error('解析结果缺少 Positively 字段');
  }
  return data;
}

let srcPath = null;
for (const p of CANDIDATES) {
  const resolved = path.resolve(p);
  if (fs.existsSync(resolved)) {
    srcPath = resolved;
    break;
  }
}

if (!srcPath) {
  console.error(
    '未找到 Personality.js。请指定路径，例如：\n' +
      '  node scripts/export_personality_data.js "e:\\xwechat_files\\...\\Personality.js"'
  );
  process.exit(1);
}

const data = loadPersonalityJs(srcPath);
fs.mkdirSync(OUT, { recursive: true });
const outPath = path.join(OUT, 'Personality.json');
fs.writeFileSync(outPath, JSON.stringify(data), 'utf8');
console.log('wrote', outPath);
console.log('from', srcPath);
console.log('keys', Object.keys(data).length, '· Positively', Object.keys(data.Positively || {}).length);
