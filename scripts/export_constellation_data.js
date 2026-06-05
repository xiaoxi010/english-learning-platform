/**
 * 将星座血型文案库复制/规范为 data/constellation.json
 * 用法:
 *   node scripts/export_constellation_data.js [源文件路径]
 * 或把云存储下载的 constellation.json 放到 data/constellation_source.json 后执行本脚本
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
  'constellation.json'
);
const CANDIDATES = [
  process.argv[2],
  process.env.CONSTELLATION_SRC,
  DEFAULT_SRC,
  path.join(OUT, 'constellation_source.json'),
  path.join(
    'C:',
    'Users',
    'HP',
    'Desktop',
    '吉致生涯',
    '吉致生涯',
    'life_code',
    'miniprogram',
    'pages',
    'constellation.json'
  ),
].filter(Boolean);

function normalizeRoot(obj) {
  if (!obj || typeof obj !== 'object') return null;
  if (obj.constellation_attribute && typeof obj.constellation_attribute === 'object') return obj;
  for (const key of ['data', 'content', 'constellationData', 'payload', 'body']) {
    const v = obj[key];
    if (v && typeof v === 'object' && !Array.isArray(v) && v.constellation_attribute) return v;
  }
  if (typeof obj.json === 'string') {
    try {
      return normalizeRoot(JSON.parse(obj.json));
    } catch (e) {
      return null;
    }
  }
  return null;
}

let srcPath = null;
for (const p of CANDIDATES) {
  if (p && fs.existsSync(p)) {
    srcPath = path.resolve(p);
    break;
  }
}

if (!srcPath) {
  console.error(
    '未找到源文件。请从微信云开发下载 constellation.json，保存为 data/constellation_source.json 后重试，或：\n' +
      '  node scripts/export_constellation_data.js <路径>'
  );
  process.exit(1);
}

const raw = fs.readFileSync(srcPath, 'utf8').replace(/^\uFEFF/, '').trim();
let obj;
if (raw.charAt(0) === '{') {
  obj = JSON.parse(raw);
} else {
  const code = raw.replace(/export\s+default\s+constellationData\s*;?\s*$/i, '').trim();
  // eslint-disable-next-line no-new-func
  obj = new Function(`${code}; return constellationData;`)();
}

const data = normalizeRoot(obj) || obj;
if (!data || !data.constellation_attribute) {
  console.error('文件缺少 constellation_attribute 字段，请确认是小程序星座文案库');
  process.exit(1);
}

fs.mkdirSync(OUT, { recursive: true });
const outPath = path.join(OUT, 'constellation.json');
fs.writeFileSync(outPath, JSON.stringify(data, null, 0), 'utf8');
console.log('wrote', outPath, 'from', srcPath);
