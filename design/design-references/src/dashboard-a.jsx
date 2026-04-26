// Variant A — "Classic": clean, info-dense, printed-journal feel
// Layout: big summary row · line chart · bar chart · insights · recent txns

function DashboardA({ currency }) {
  const { t, lang } = useT();
  const monthE = SAMPLE.daily.reduce((a, d) => a + d.expense, 0);
  const monthI = SAMPLE.daily.reduce((a, d) => a + d.income, 0);
  const net = monthI - monthE;

  const today = { en: 'Tuesday, April 21', ja: '4月21日(火)', zh: '4月21日 · 星期二' }[lang];
  const shaping = { en: "Here's how April is shaping up \u2014 9 days left.", ja: '4月の進み具合 \u2014 残り9日。', zh: '四月还剩 9 天，进度如图。' }[lang];
  const balance = { en: 'Balance', ja: '残高', zh: '余额' }[lang];
  const incomeApr = { en: 'Income (Apr)', ja: '収入(4月)', zh: '收入(4月)' }[lang];
  const expenseApr = { en: 'Expense (Apr)', ja: '支出(4月)', zh: '支出(4月)' }[lang];
  const netL = { en: 'Net', ja: '収支', zh: '净额' }[lang];
  const across = { en: 'across 3 accounts', ja: '3口座合計', zh: '3 个账户合计' }[lang];
  const payrolls = { en: '2 payrolls + 1 refund', ja: '給与2件 + 返金1件', zh: '2 笔工资 + 1 笔退款' }[lang];
  const txns247 = { en: '247 transactions', ja: '247件', zh: '247 笔交易' }[lang];
  const savingRate = { en: 'saving rate 32%', ja: '貯蓄率 32%', zh: '储蓄率 32%' }[lang];
  const goal25 = { en: 'goal: 25%', ja: '目標: 25%', zh: '目标: 25%' }[lang];
  const onTrack = { en: 'on track', ja: '順調', zh: '达标' }[lang];
  const vsMar = { en: '\u221212% vs. Mar', ja: '\u221212% (3月比)', zh: '环比 \u221212%' }[lang];
  const trendVs = { en: '+2.1%', ja: '+2.1%', zh: '+2.1%' }[lang];
  const daily = { en: 'Daily flow', ja: '日次の収支', zh: '每日收支' }[lang];
  const range = { en: 'Apr 1 \u2013 30', ja: '4月1日 \u2013 30日', zh: '4月1日 \u2013 30日' }[lang];
  const expL = { en: 'Expense', ja: '支出', zh: '支出' }[lang];
  const incL = { en: 'Income',  ja: '収入', zh: '收入' }[lang];
  const cats = { en: 'Categories', ja: 'カテゴリ', zh: '分类占比' }[lang];
  const thisMo = { en: 'this month', ja: '今月', zh: '本月' }[lang];
  const trend12 = { en: '12-month trend', ja: '12ヶ月の推移', zh: '近 12 个月走势' }[lang];
  const expVsInc = { en: 'Expense vs. Income', ja: '支出 vs 収入', zh: '支出 vs 收入' }[lang];
  const day = { en: 'Day', ja: '日', zh: '日' }[lang];
  const week = { en: 'Week', ja: '週', zh: '周' }[lang];
  const bar = { en: 'Bar', ja: '棒', zh: '柱状' }[lang];
  const stacked = { en: 'Stacked', ja: '積み上げ', zh: '堆叠' }[lang];
  const autoExtracted = { en: 'Auto-extracted from screenshots + bank sync', ja: 'スクリーンショット + 銀行連携から自動抽出', zh: '由截图 + 银行同步自动提取' }[lang];
  const viewAll = { en: 'View all', ja: 'すべて見る', zh: '查看全部' }[lang];

  return (
    <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '20px 24px 120px' }}>
      {/* Hero greeting */}
      <div style={{ marginBottom: 20, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 20 }}>
        <div>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.2, color: 'var(--ink-500)', marginBottom: 4 }}>
            {today}
          </div>
          <h1 className="hand" style={{ fontSize: 32, fontWeight: 700, color: 'var(--ink-900)', letterSpacing: -0.3 }}>
            {t('greet_afternoon')} <span className="hand" style={{ fontSize: 32, color: 'var(--accent-amber)' }}>✦</span>
          </h1>
          <div style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 3 }}>
            {shaping}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <APButton variant="outline" size="md" icon="refresh-ccw">{t('sync')}</APButton>
          <APButton variant="primary" size="md" icon="plus">{t('add_record')}</APButton>
        </div>
      </div>

      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 18 }}>
        <KpiCard label={balance} value={fmtMoney(8420.33, currency)} trend={trendVs} tone="neutral" sub={across} />
        <KpiCard label={incomeApr} value={fmtMoney(monthI, currency)} trend={onTrack} tone="good" sub={payrolls} />
        <KpiCard label={expenseApr} value={fmtMoney(monthE, currency)} trend={vsMar} tone="good" sub={txns247} />
        <KpiCard label={netL} value={fmtMoney(net, currency)} trend={savingRate} tone="good" sub={goal25} highlight />
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 14, marginBottom: 18 }}>
        <PaperCard>
          <ChartHeader title={daily} sub={range} tabs={[day, week]} />
          <LineChart data={SAMPLE.daily} currency={currency} height={200} />
          <ChartLegend items={[
            { label: expL, color: 'var(--neg-500)' },
            { label: incL, color: 'var(--pos-500)' },
          ]}/>
        </PaperCard>

        <PaperCard>
          <ChartHeader title={cats} sub={thisMo} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <DonutChart data={SAMPLE.categoryBreakdown} currency={currency} size={150} />
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 7 }}>
              {SAMPLE.categoryBreakdown.map(c => (
                <div key={c.cat} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 4, background: CAT_COLORS[c.cat].dot }}/>
                  <span style={{ flex: 1, color: 'var(--ink-700)' }}>{c.cat}</span>
                  <span style={{ color: 'var(--ink-500)', fontVariantNumeric: 'tabular-nums' }}>{c.pct}%</span>
                </div>
              ))}
            </div>
          </div>
        </PaperCard>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 14, marginBottom: 18 }}>
        <PaperCard>
          <ChartHeader title={trend12} sub={expVsInc} tabs={[bar, stacked]} />
          <BarChart data={SAMPLE.monthly} currency={currency} height={200} />
        </PaperCard>

        <PaperCard padding={0}>
          <div style={{ padding: '18px 20px 10px', borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <div className="brand-hand" style={{ fontSize: 22, color: 'var(--ink-900)', letterSpacing: -0.3 }}>MITA's notes</div>
            <span style={{ fontSize: 11, padding: '2px 7px', borderRadius: 6, background: 'var(--cream-200)', color: 'var(--ink-500)' }}>4 {t('insights')}</span>
          </div>
          <div style={{ padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 240, overflow: 'auto' }} className="scroll-thin">
            {SAMPLE.insights.map(it => <InsightRow key={it.id} insight={it} />)}
          </div>
        </PaperCard>
      </div>

      {/* Recent transactions */}
      <PaperCard padding={0}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--ink-900)' }}>{t('recent_records')}</div>
            <div style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>{autoExtracted}</div>
          </div>
          <div style={{ flex: 1 }} />
          <APButton variant="ghost" size="sm" iconRight="arrow-right">{viewAll}</APButton>
        </div>
        <TxnTable rows={SAMPLE.transactions.slice(0, 7)} currency={currency} />
      </PaperCard>
    </div>
  );
}

function KpiCard({ label, value, trend, sub, tone = 'neutral', highlight }) {
  const toneColor = tone === 'good' ? 'var(--pos-500)' : tone === 'bad' ? 'var(--neg-500)' : 'var(--ink-500)';
  return (
    <PaperCard style={highlight ? { background: 'linear-gradient(160deg, var(--cream-200), var(--cream-100))', borderColor: 'var(--cream-400)' } : {}}>
      <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.9, color: 'var(--ink-500)', fontWeight: 600 }}>{label}</div>
      <div className="serif num" style={{ fontSize: 26, fontWeight: 500, color: 'var(--ink-900)', marginTop: 4, letterSpacing: -0.5, fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8, fontSize: 11.5 }}>
        <span style={{ color: toneColor, fontWeight: 600 }}>{trend}</span>
        <span style={{ color: 'var(--ink-400)' }}>· {sub}</span>
      </div>
    </PaperCard>
  );
}

function ChartHeader({ title, sub, tabs }) {
  const [active, setActive] = React.useState(tabs ? tabs[0] : null);
  return (
    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12, gap: 10 }}>
      <div>
        <div style={{ fontSize: 14.5, fontWeight: 600, color: 'var(--ink-900)' }}>{title}</div>
        {sub && <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>{sub}</div>}
      </div>
      <div style={{ flex: 1 }} />
      {tabs && (
        <SegmentedToggle
          options={tabs.map(t => ({ id: t, label: t }))}
          value={active} onChange={setActive} />
      )}
    </div>
  );
}

function ChartLegend({ items }) {
  return (
    <div style={{ display: 'flex', gap: 14, marginTop: 4 }}>
      {items.map(it => (
        <div key={it.label} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: 'var(--ink-500)' }}>
          <span style={{ width: 10, height: 2, borderRadius: 1, background: it.color }} />
          {it.label}
        </div>
      ))}
    </div>
  );
}

function InsightRow({ insight }) {
  const toneBg = { warn: 'var(--neg-50)', good: 'var(--pos-50)', info: 'var(--cream-200)' }[insight.tone];
  const toneIcon = { warn: 'triangle-alert', good: 'check', info: 'sparkles' }[insight.tone];
  const toneColor = { warn: 'var(--neg-500)', good: 'var(--pos-500)', info: 'var(--accent-amber)' }[insight.tone];
  return (
    <div style={{ display: 'flex', gap: 10, padding: 10, borderRadius: 9, alignItems: 'flex-start' }}
      onMouseEnter={e => e.currentTarget.style.background = 'var(--cream-100)'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
      <div style={{ width: 28, height: 28, borderRadius: 8, background: toneBg, color: toneColor, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <Icon name={toneIcon} size={14} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink-900)' }}>{insight.title}</div>
        <div style={{ fontSize: 11.5, color: 'var(--ink-500)', lineHeight: 1.45, marginTop: 1 }}>{insight.body}</div>
        <button style={{
          marginTop: 4, fontSize: 11, fontWeight: 600, color: toneColor,
          background: 'transparent', border: 'none', padding: 0, cursor: 'pointer', fontFamily: 'var(--font-sans)',
        }}>{insight.action} →</button>
      </div>
    </div>
  );
}

function TxnTable({ rows, currency }) {
  return (
    <div style={{ padding: 0 }}>
      {rows.map((t, i) => {
        const isIncome = t.amt > 0;
        return (
          <div key={t.id} style={{
            display: 'grid', gridTemplateColumns: '76px 1fr 110px 110px 80px',
            padding: '11px 20px', alignItems: 'center', gap: 12,
            borderBottom: i < rows.length - 1 ? '1px solid var(--ink-100)' : 'none',
            fontSize: 13, fontFamily: 'var(--font-sans)',
          }}>
            <div style={{ color: 'var(--ink-500)', fontSize: 11.5 }}>
              <div style={{ color: 'var(--ink-700)', fontWeight: 600, fontSize: 12 }}>{t.date}</div>
              {t.time}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ color: 'var(--ink-900)', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.merchant}</div>
              {t.note && <div style={{ fontSize: 11, color: 'var(--ink-500)', fontStyle: 'italic' }}>{t.note}</div>}
            </div>
            <CatPill cat={t.cat} size="sm" />
            <SourceTag src={t.src} />
            <div className="num" style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 600, color: isIncome ? 'var(--pos-500)' : 'var(--ink-900)' }}>
              {isIncome ? '+' : ''}{fmtMoney(t.amt, currency)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SourceTag({ src }) {
  const map = {
    screenshot: { label: 'screenshot', icon: 'image',   bg: 'var(--cream-200)', fg: 'var(--ink-700)' },
    manual:     { label: 'manual',     icon: 'pencil',  bg: 'var(--cream-100)', fg: 'var(--ink-500)' },
    recurring:  { label: 'recurring',  icon: 'refresh-ccw', bg: '#E5E0F3', fg: '#4A3F7A' },
    bank:       { label: 'bank',       icon: 'link',    bg: '#DCE5F3', fg: '#2F4E84' },
  }[src] || { label: src, icon: 'file', bg: 'var(--cream-200)', fg: 'var(--ink-500)' };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5, padding: '2px 8px',
      fontSize: 10.5, borderRadius: 6, background: map.bg, color: map.fg, fontWeight: 500,
    }}>
      <Icon name={map.icon} size={10} />
      {map.label}
    </span>
  );
}

Object.assign(window, { DashboardA, KpiCard, ChartHeader, ChartLegend, InsightRow, TxnTable, SourceTag });
