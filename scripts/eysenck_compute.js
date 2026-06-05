/**
 * 艾克森测评计分 + 报告视图模型（供 Flask 子进程调用）
 * 用法: node eysenck_compute.js <answers_json> <user_info_json>
 */
const path = require('path')
const MINI_UTILS =
  process.env.EYSENCK_MINI_UTILS ||
  'C:/Users/HP/Desktop/吉致生涯/吉致生涯/life_code/miniprogram/utils'
const db = require(path.join(MINI_UTILS, '艾克森情绪稳定性测评数据库.js'))
const tpl = require(path.join(MINI_UTILS, '艾克森情绪稳定性测评参考模板-仅供参考.js'))

function main() {
  const answers = JSON.parse(process.argv[2] || '[]')
  const userInfo = JSON.parse(process.argv[3] || '{}')
  const test = new db.EysenckEmotionTest()
  test.setAnswers(answers)
  const result = test.run()
  if (!result) {
    process.stdout.write(JSON.stringify({ ok: false, error: 'incomplete' }))
    process.exit(1)
  }
  const vm = tpl.prepareReportViewModel(result, userInfo)
  process.stdout.write(JSON.stringify({ ok: true, result, vm }))
}

try {
  main()
} catch (e) {
  process.stdout.write(JSON.stringify({ ok: false, error: String(e.message || e) }))
  process.exit(1)
}
