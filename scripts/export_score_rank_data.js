/**
 * 将小程序云存储「一分一段」JSON 复制到 data/score_rank/
 * 用法:
 *   node scripts/export_score_rank_data.js [源目录]
 *
 * 源目录：从微信云开发控制台下载的全部 JSON，或本地缓存目录。
 * 文件名需与 miniprogram/utils/scoreRankCloud.js 中 PROVINCE_FILES 一致。
 */
const fs = require('fs');
const path = require('path');

const OUT = path.join(__dirname, '..', 'data', 'score_rank');

const PROVINCE_FILES = {
  吉林: '吉林省2025一分一段.json',
  上海: '上海_2025一分一段.json',
  云南: '云南_2025一分一段.json',
  内蒙古: '内蒙古_2025一分一段.json',
  北京: '北京_2025一分一段.json',
  四川: '四川_2025一分一段.json',
  天津: '天津_2025一分一段.json',
  宁夏: '宁夏_2025一分一段.json',
  安徽: '安徽_2025一分一段.json',
  山东: '山东_2025一分一段.json',
  山西: '山西_2025一分一段.json',
  广东: '广东_2025一分一段.json',
  广西: '广西_2025一分一段.json',
  新疆: '新疆_2025一分一段.json',
  江苏: '江苏_2025一分一段.json',
  江西: '江西_2025一分一段.json',
  河北: '河北_2025一分一段.json',
  河南: '河南_2025一分一段.json',
  浙江: '浙江_2025一分一段.json',
  海南: '海南_2025一分一段.json',
  湖北: '湖北_2025一分一段.json',
  湖南: '湖南_2025一分一段.json',
  甘肃: '甘肃_2025一分一段.json',
  福建: '福建_2025一分一段.json',
  贵州: '贵州_2025一分一段.json',
  辽宁: '辽宁_2025一分一段.json',
  重庆: '重庆_2025一分一段.json',
  陕西: '陕西_2025一分一段.json',
  青海: '青海_2025一分一段.json',
  黑龙江: '黑龙江_2025一分一段.json',
};

const CANDIDATE_SRC = [
  process.argv[2],
  process.env.SCORE_RANK_SRC,
  path.join('C:', 'Users', 'HP', 'Desktop', '吉致生涯', '一分一段'),
  path.join('C:', 'Users', 'HP', 'Downloads', '一分一段'),
].filter(Boolean);

function findSrc() {
  for (const dir of CANDIDATE_SRC) {
    if (dir && fs.existsSync(dir) && fs.statSync(dir).isDirectory()) {
      const hit = Object.values(PROVINCE_FILES).some((f) =>
        fs.existsSync(path.join(dir, f))
      );
      if (hit) return dir;
    }
  }
  return null;
}

function main() {
  const src = findSrc();
  if (!src) {
    console.error('未找到源目录。请从微信云开发下载 JSON 后执行:');
    console.error('  node scripts/export_score_rank_data.js "你的目录路径"');
    console.error('目标目录:', OUT);
    process.exit(1);
  }
  fs.mkdirSync(OUT, { recursive: true });
  let ok = 0;
  let miss = 0;
  for (const [prov, file] of Object.entries(PROVINCE_FILES)) {
    const from = path.join(src, file);
    const to = path.join(OUT, file);
    if (!fs.existsSync(from)) {
      console.warn('缺失:', prov, file);
      miss += 1;
      continue;
    }
    fs.copyFileSync(from, to);
    console.log('已复制:', file);
    ok += 1;
  }
  fs.writeFileSync(
    path.join(OUT, '_manifest.json'),
    JSON.stringify({ source: src, copied: ok, missing: miss, files: PROVINCE_FILES }, null, 2),
    'utf8'
  );
  console.log(`完成：${ok} 个文件 -> ${OUT}，缺失 ${miss} 个`);
}

main();
