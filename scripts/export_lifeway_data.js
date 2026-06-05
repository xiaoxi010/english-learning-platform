/**
 * 将 lifeway.js（人生道路解读文案库）导出为 data/lifeway.json
 * 用法:
 *   node scripts/export_lifeway_data.js
 *   node scripts/export_lifeway_data.js "路径/lifeway.js"
 */
const fs = require('fs');
const path = require('path');

const OUT = path.join(__dirname, '..', 'data');
const DEFAULT_SRC = path.join(
  'e:',
  'xwechat_files',
  'wxid_6kz7tqac90kx22_67a2',
  'msg',
  'file',
  '2026-05',
  'lifeway.js'
);

const CANDIDATES = [
  process.argv[2],
  process.env.LIFEWAY_SRC,
  DEFAULT_SRC,
  path.join(OUT, 'lifeway.js'),
  path.join(OUT, 'lifeway_source.js'),
].filter(Boolean);

function loadLifewayJs(filePath) {
  const resolved = path.resolve(filePath);
  delete require.cache[resolved];
  const mod = require(resolved);
  const data = mod.Data || mod.default || mod;
  if (!data || typeof data !== 'object' || !data.person_year_word) {
    throw new Error('解析结果缺少 person_year_word 字段');
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
    '未找到 lifeway.js。请指定路径，例如：\n' +
      '  node scripts/export_lifeway_data.js "e:\\xwechat_files\\...\\lifeway.js"'
  );
  process.exit(1);
}

const data = loadLifewayJs(srcPath);
fs.mkdirSync(OUT, { recursive: true });
const outPath = path.join(OUT, 'lifeway.json');
fs.writeFileSync(outPath, JSON.stringify(data), 'utf8');
console.log('wrote', outPath);
console.log('from', srcPath);
console.log('keys', Object.keys(data).length);
