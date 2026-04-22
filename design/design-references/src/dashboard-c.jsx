// Variant C — "Control room": data-dense cockpit with tiles + spark rows

function DashboardC({ currency }) {
  const monthE = SAMPLE.daily.reduce((a, d) => a + d.expense, 0);
  const monthI = SAMPLE.daily.reduce((a, d) => a + d.income, 0);
  const net = monthI - monthE;
  const budget = 2400;
  const budgetPct = (monthE / budget) * 100;

  return (
    <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '16px 20px 120px' }}>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 14, gap: 12 }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: 1.2, textTransform: 'uppercase', color: 'var(--ink-500)' }}>Dashboard · April 2026</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--ink-900)' }}>Personal ledger</div>
        </div>
        <div style={{ flex: 1 }} />
        <SegmentedToggle options={[{id:'w',label:'Week'},{id:'m',label:'Month'},{id:'q',label:'Quarter'},{id:'y',label:'Year'}]} value="m" onChange={()=>{}}/>
        <APButton variant="outline" size="sm" icon="download">Export</APButton>
        <APButton variant="primary" size="sm" icon="plus">New</APButton>
      </div>

      {/* Top 4-up KPI with sparks */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 12 }}>
        <SparkKpi label="Net balance" value={fmtMoney(8420, currency)} delta="+2.1%" deltaTone="good" spark={[12,14,13,16,18,17,20,19,22,24,23,26]} />
        <SparkKpi label="April income" value={fmtMoney(monthI, currency)} delta="+4.2%" deltaTone="good" spark={[14,14,14,15,15,16,17,17,18,18,20,21]} />
        <SparkKpi label="April expense" value={fmtMoney(monthE, currency)} delta="−12%" deltaTone="good" spark={[22,20,18,17,17,15,14,14,13,12,12,10]} />
        <SparkKpi label="Savings rate" value="32%" delta="goal 25%" deltaTone="good" spark={[18,20,19,22,25,24,27,28,30,31,32,32]} />
      </div>

      {/* Budget bar */}
      <PaperCard style={{ marginBottom: 12 }} padding={16}>
        <div style={{ display: 'flex', alignItems: 'baseline', marginBottom: 8, gap: 10 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>Month budget</div>
          <div style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>9 days left · projected {fmtMoney(monthE * 30 / 21, currency)}</div>
          <div style={{ flex: 1 }} />
          <div style={{ fontSize: 13, fontVariantNumeric: 'tabular-nums', color: 'var(--ink-700)' }}>
            <strong style={{ color: 'var(--ink-900)' }}>{fmtMoney(monthE, currency)}</strong>
            <span style={{ color: 'var(--ink-400)' }}> of {fmtMoney(budget, currency)}</span>
          </div>
        </div>
        <div style={{ height: 10, background: 'var(--cream-200)', borderRadius: 5, overflow: 'hidden', position: 'relative' }}>
          <div style={{ width: `${Math.min(budgetPct, 100)}%`, height: '100%', background: budgetPct > 100 ? 'var(--neg-500)' : 'linear-gradient(90deg, var(--cream-400), var(--accent-amber))', borderRadius: 5 }}/>
          <div style={{ position: 'absolute', left: '70%', top: -3, bottom: -3, width: 2, background: 'var(--ink-400)' }} title="expected pace (70%)"/>
        </div>
      </PaperCard>

      {/* Main grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <PaperCard padding={16}>
          <ChartHeader title="Daily flow" sub="Apr 1 – 30" tabs={['Day','Cumul.']} />
          <LineChart data={SAMPLE.daily} currency={currency} height={180} />
        </PaperCard>
        <PaperCard padding={16}>
          <ChartHeader title="12-month" sub="expense vs. income" />
          <BarChart data={SAMPLE.monthly} currency={currency} height={180} />
        </PaperCard>
      </div>

      {/* Insights + categories grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr 1.3fr', gap: 12, marginBottom: 12 }}>
        <PaperCard padding={16}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
            <Icon name="sparkles" size={15} />
            <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-900)' }}>Agent suggestions</div>
            <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: 'var(--accent-amber)', color: '#fff', fontWeight: 700 }}>4</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {SAMPLE.insights.map(i => <InsightRow key={i.id} insight={i}/>)}
          </div>
        </PaperCard>

        <PaperCard padding={16}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-900)', marginBottom: 12 }}>Top categories</div>
          <DonutChart data={SAMPLE.categoryBreakdown} currency={currency} size={140} />
          <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 11.5 }}>
            {SAMPLE.categoryBreakdown.slice(0, 6).map(c => (
              <div key={c.cat} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ width: 7, height: 7, borderRadius: 4, background: CAT_COLORS[c.cat].dot }}/>
                <span style={{ flex: 1, color: 'var(--ink-700)' }}>{c.cat}</span>
                <span style={{ color: 'var(--ink-500)', fontVariantNumeric: 'tabular-nums' }}>{c.pct}%</span>
              </div>
            ))}
          </div>
        </PaperCard>

        <PaperCard padding={0}>
          <div style={{ padding: '14px 16px 10px', borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center' }}>
            <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-900)' }}>Recent activity</div>
            <div style={{ flex: 1 }} />
            <APButton variant="ghost" size="sm" iconRight="arrow-right">All</APButton>
          </div>
          <TxnTable rows={SAMPLE.transactions.slice(0, 6)} currency={currency} />
        </PaperCard>
      </div>

      {/* Goals strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <GoalCard emoji="✈" title="Kyoto trip" current={1240} target={2400} currency={currency} due="Jun 15" />
        <GoalCard emoji="💻" title="New laptop" current={820}  target={1800} currency={currency} due="Aug 1"  />
        <GoalCard emoji="🏔" title="Emergency fund" current={4200} target={6000} currency={currency} due="Dec 31" />
      </div>
    </div>
  );
}

function SparkKpi({ label, value, delta, deltaTone, spark }) {
  const max = Math.max(...spark), min = Math.min(...spark);
  const w = 90, h = 28;
  const path = spark.map((v, i) => `${i === 0 ? 'M' : 'L'}${(i / (spark.length - 1)) * w},${h - ((v - min) / (max - min || 1)) * h}`).join(' ');
  const tc = deltaTone === 'good' ? 'var(--pos-500)' : deltaTone === 'bad' ? 'var(--neg-500)' : 'var(--ink-500)';
  return (
    <PaperCard padding={14}>
      <div style={{ fontSize: 10.5, textTransform: 'uppercase', letterSpacing: 0.8, color: 'var(--ink-500)', fontWeight: 600 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, marginTop: 4 }}>
        <div className="serif" style={{ fontSize: 22, fontWeight: 500, color: 'var(--ink-900)', fontVariantNumeric: 'tabular-nums', letterSpacing: -0.5, lineHeight: 1 }}>{value}</div>
        <div style={{ flex: 1 }} />
        <svg width={w} height={h} style={{ flexShrink: 0 }}>
          <path d={path} fill="none" stroke={tc} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
          <path d={`${path} L${w},${h} L0,${h} Z`} fill={tc} opacity="0.12"/>
        </svg>
      </div>
      <div style={{ fontSize: 11, color: tc, fontWeight: 600, marginTop: 4 }}>{delta}</div>
    </PaperCard>
  );
}

function GoalCard({ emoji, title, current, target, currency, due }) {
  const pct = Math.round((current / target) * 100);
  return (
    <PaperCard padding={16}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <div style={{ width: 32, height: 32, borderRadius: 9, background: 'var(--cream-200)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>{emoji}</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>{title}</div>
          <div style={{ fontSize: 10.5, color: 'var(--ink-500)' }}>due {due}</div>
        </div>
        <div className="hand" style={{ fontSize: 20, color: 'var(--accent-amber)', fontWeight: 700 }}>{pct}%</div>
      </div>
      <div style={{ height: 6, background: 'var(--cream-200)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, var(--cream-400), var(--accent-amber))' }}/>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--ink-500)', marginTop: 5, fontVariantNumeric: 'tabular-nums' }}>
        <span>{fmtMoney(current, currency)}</span>
        <span>of {fmtMoney(target, currency)}</span>
      </div>
    </PaperCard>
  );
}

Object.assign(window, { DashboardC, SparkKpi, GoalCard });
