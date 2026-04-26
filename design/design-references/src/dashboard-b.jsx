// Variant B — "Journal": handwritten, diary-style, one focused column
// Emphasizes the agent's voice, uses handwritten type + sketchy accents

function DashboardB({ currency }) {
  const { t, lang, name } = useT();
  const monthE = SAMPLE.daily.reduce((a, d) => a + d.expense, 0);
  const monthI = SAMPLE.daily.reduce((a, d) => a + d.income, 0);
  const net = monthI - monthE;

  const issue = { en: 'Monthly ledger · issue 04', ja: '月刃帳 · 第04号', zh: '月刊帐本 · 第 04 期' }[lang];
  const title = { en: "April, '26", ja: '2026年 4月', zh: '二〇二六年 · 四月' }[lang];
  const subBest = { en: 'your best run since November.', ja: '11月以来のベスト。', zh: '是去年 11 月以来最好的一次。' }[lang];
  const rate = { en: '32% savings rate', ja: '貯蓄率 32%', zh: '储蓄率 32%' }[lang];
  const spent = { en: 'spent', ja: '支出', zh: '支出' }[lang];
  const earned = { en: 'earned', ja: '収入', zh: '收入' }[lang];
  const noteLabel = { en: 'A note from MITA', ja: 'MITAからの一筆', zh: 'MITA 的一封短信' }[lang];
  const letter = {
    en: <>Hey {name} — good month. I noticed your coffee spend is creeping up (<span style={{ color: 'var(--neg-500)', fontWeight: 700 }}>+42%</span> vs. March), but your grocery runs to Trader Joe's replaced two DoorDash orders per week — that alone saved you about <span className="doodle-underline" style={{ fontWeight: 700 }}>$95</span>.<br/><br/>Netflix ($15.49/mo) hasn't been opened in 21 days — want me to cancel? And payday's Friday; historically you overspend ~18% the three days after, so I'd like to auto-sweep <strong> {fmtMoney(400, currency)}</strong> into savings before it hits.</>,
    ja: <>{name}さんおつかれさま、今月はいい感じです。コーヒー代がちょっと伸び気味（<span style={{ color: 'var(--neg-500)', fontWeight: 700 }}>+42%</span> 3月比）ですが、周 2 回のデリバリーがスーパーに置き換わり、<span className="doodle-underline" style={{ fontWeight: 700 }}>¥9,500</span> ほど浮きました。<br/><br/>Netflix (¡1,480/月) は 21日間開いていません。解約しますか？金曜日が給料日で、までの傾向ではその後 3 日間で 18% ほど使い過ぎています。<strong> {fmtMoney(400, currency)}</strong> を先に貯蓄に退避しておきませんか？</>,
    zh: <>{name}，这个月过得不错。哖啡开支里稍稍有点爬升（环比 <span style={{ color: 'var(--neg-500)', fontWeight: 700 }}>+42%</span>），不过每周两次的 Trader Joe's 替掉了两次外卖，光这一项就省了大约 <span className="doodle-underline" style={{ fontWeight: 700 }}>¥680</span>。<br/><br/>Netflix（¥110/月）已经 21 天没打开了 — 要不要取消？周五发工资，按你过去的习惯，接下来三天往往超支 18%。我想提前把 <strong> {fmtMoney(400, currency)}</strong> 转进储蓄，可以么？</>,
  }[lang];
  const btnSweep = { en: 'Auto-sweep $400', ja: '¥40,000を自動退避', zh: '自动转 $400' }[lang];
  const btnReview = { en: 'Review Netflix', ja: 'Netflixを見る', zh: '查看 Netflix' }[lang];
  const btnMore = { en: 'More insights', ja: '他の気づき', zh: '更多建议' }[lang];
  const records = { en: 'Records', ja: '件数', zh: '条数' }[lang];
  const screenshots = { en: 'Screenshots', ja: 'スクリショ', zh: '截图' }[lang];
  const manualEntries = { en: 'Manual entries', ja: '手入力', zh: '手动录入' }[lang];
  const largest = { en: 'Largest spend', ja: '最大支出', zh: '最大支出' }[lang];
  const avgD = { en: 'Avg. daily', ja: '日平均', zh: '日均' }[lang];
  const subParsed = { en: 'auto-parsed', ja: '自動解析', zh: '自动解析' }[lang];
  const subRent = { en: 'rent · Apr 1', ja: '家賃 · 4/1', zh: '房租 · 4/1' }[lang];
  const quote = { en: '“Small leaks sink great ships.”', ja: '「小さな漏れが大船を沈める。」', zh: '“小洞不补，大船容易沉。”' }[lang];
  const quoteAttr = { en: '— Benjamin Franklin, misquoted by MITA', ja: '— フランクリン(MITA訳)', zh: '— 富兰克林，MITA 转述' }[lang];

  return (
    <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '28px 40px 120px', background: 'var(--cream-100)' }}>
      <div style={{ maxWidth: 1040, margin: '0 auto' }}>

        {/* Masthead */}
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', borderBottom: '2px solid var(--ink-700)', paddingBottom: 10, marginBottom: 22 }}>
          <div>
            <div style={{ fontSize: 10.5, textTransform: 'uppercase', letterSpacing: 2, color: 'var(--ink-500)' }}>{issue}</div>
            <div className="serif" style={{ fontSize: 42, fontWeight: 500, color: 'var(--ink-900)', letterSpacing: -1, marginTop: 2 }}>
              {title}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div className="hand" style={{ fontSize: 18, color: 'var(--ink-500)' }}>{t('by_mita')}</div>
            <div style={{ fontSize: 11, color: 'var(--ink-400)' }}>{t('last_synced')}</div>
          </div>
        </div>

        {/* Big number */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 24, marginBottom: 28, alignItems: 'center' }}>
          <div>
            <div className="hand" style={{ fontSize: 22, color: 'var(--ink-700)', marginBottom: 6 }}>
              {t('you_saved')}
            </div>
            <div className="serif num" style={{ fontSize: 82, fontWeight: 500, color: 'var(--pos-500)', letterSpacing: -2.5, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
              {fmtMoney(net, currency)}
            </div>
            <div className="hand-body" style={{ fontSize: 16, color: 'var(--ink-500)', marginTop: 6 }}>
              <span className="doodle-underline">{rate}</span> — {subBest}
            </div>
          </div>

          <PaperCard padding={20} style={{ background: 'var(--cream-50)' }}>
            <div className="hand" style={{ fontSize: 20, color: 'var(--ink-900)', marginBottom: 10 }}>{t('shape_of')}</div>
            <LineChart data={SAMPLE.daily} currency={currency} height={160} />
            <div style={{ display: 'flex', gap: 14, marginTop: 8, fontSize: 11.5, color: 'var(--ink-500)' }}>
              <span><span style={{ color: 'var(--neg-500)', fontWeight: 700 }}>—</span> {spent} <Num>{fmtMoney(monthE, currency)}</Num></span>
              <span><span style={{ color: 'var(--pos-500)', fontWeight: 700 }}>—</span> {earned} <Num>{fmtMoney(monthI, currency)}</Num></span>
            </div>
          </PaperCard>
        </div>

        {/* Agent's letter */}
        <PaperCard padding={28} style={{ background: 'var(--cream-50)', marginBottom: 20, position: 'relative' }}>
          <div style={{ position: 'absolute', top: -10, left: 20, background: 'var(--cream-300)', padding: '2px 10px', borderRadius: 6, fontSize: 10.5, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', color: 'var(--ink-900)' }}>{noteLabel}</div>
          <div className="hand-body" style={{ fontSize: 16, lineHeight: 1.85, color: 'var(--ink-700)' }}>
            {letter}
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <APButton variant="primary" size="sm">{btnSweep}</APButton>
            <APButton variant="outline" size="sm">{btnReview}</APButton>
            <APButton variant="ghost" size="sm">{btnMore}</APButton>
          </div>
        </PaperCard>

        {/* Three columns: stats, top categories, recent */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.1fr 1.4fr', gap: 16, marginBottom: 20 }}>
          <PaperCard>
            <div className="hand" style={{ fontSize: 18, color: 'var(--ink-900)', marginBottom: 12 }}>{t('by_the_numbers')}</div>
            {[
              [records, '247', t('records_sub').split(' · ')[0] || ''],
              [screenshots, '184', subParsed],
              [manualEntries, '63', ''],
              [largest, fmtMoney(340, currency), subRent],
              [avgD, fmtMoney(monthE / 30, currency), ''],
            ].map(([k, v, s], i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '8px 0', borderBottom: i < 4 ? '1px dashed var(--ink-200)' : 'none' }}>
                <div>
                  <div style={{ fontSize: 12.5, color: 'var(--ink-700)' }}>{k}</div>
                  {s && <div style={{ fontSize: 10.5, color: 'var(--ink-400)' }}>{s}</div>}
                </div>
                <div className="serif num" style={{ fontSize: 18, fontWeight: 500, color: 'var(--ink-900)', fontVariantNumeric: 'tabular-nums' }}>{v}</div>
              </div>
            ))}
          </PaperCard>

          <PaperCard>
            <div className="hand" style={{ fontSize: 18, color: 'var(--ink-900)', marginBottom: 12 }}>{t('where_it_went')}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
              {SAMPLE.categoryBreakdown.map(c => (
                <div key={c.cat}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, color: 'var(--ink-700)', marginBottom: 4 }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ width: 8, height: 8, borderRadius: 4, background: CAT_COLORS[c.cat].dot }}/>
                      {c.cat}
                    </span>
                    <span className="num" style={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{fmtMoney(c.amt, currency)}</span>
                  </div>
                  <div style={{ height: 5, background: 'var(--ink-100)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${c.pct * 2.2}%`, maxWidth: '100%', height: '100%', background: CAT_COLORS[c.cat].dot, borderRadius: 3 }}/>
                  </div>
                </div>
              ))}
            </div>
          </PaperCard>

          <PaperCard padding={0}>
            <div style={{ padding: '14px 18px 10px', borderBottom: '1px solid var(--ink-200)' }}>
              <div className="hand" style={{ fontSize: 18, color: 'var(--ink-900)' }}>{t('lately')}</div>
              <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>{t('latest_5')}</div>
            </div>
            <TxnTable rows={SAMPLE.transactions.slice(0, 5)} currency={currency} />
          </PaperCard>
        </div>

        {/* Footer quote */}
        <div style={{ textAlign: 'center', padding: '20px 0 40px', borderTop: '1px solid var(--ink-200)' }}>
          <div className="hand" style={{ fontSize: 22, color: 'var(--ink-400)', fontStyle: 'italic' }}>
            {quote}
          </div>
          <div style={{ fontSize: 10.5, color: 'var(--ink-400)', marginTop: 4, letterSpacing: 1, textTransform: 'uppercase' }}>{quoteAttr}</div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { DashboardB });
