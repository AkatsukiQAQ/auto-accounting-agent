// New screens: Accounts, Transfer-aware Records support, Recurring, Review queue.
// Budget already exists — we replace with a richer version via BudgetScreenV2.
// Keep everything in the cream/ink paper aesthetic already established.

// ──────────────────────────────────────────────────────────
// Shared sample data for the new screens
// ──────────────────────────────────────────────────────────
const NEW_SAMPLE = {
  accounts: [
    { id: 'boa',    name: 'Bank of America · Checking', kind: 'bank',    last4: '4821', balance: 3842.10, color: '#C2263A', icon: '🏦', trend: [3100,3400,3200,3900,3842] },
    { id: 'chase',  name: 'Chase · Savings',            kind: 'savings', last4: '7103', balance: 12480.00, color: '#117ACA', icon: '💰', trend: [9800,10200,10900,11500,12480] },
    { id: 'amex',   name: 'Amex · Gold',                kind: 'credit',  last4: '1009', balance: -842.36, limit: 8000, color: '#D4A24C', icon: '💳', trend: [-200,-340,-580,-710,-842] },
    { id: 'alipay', name: '支付宝',                       kind: 'wallet',  last4: '—',    balance: 128.44,  color: '#1677FF', icon: '🇨🇳', trend: [300,220,180,150,128] },
    { id: 'cash',   name: 'Cash · wallet',              kind: 'cash',    last4: '—',    balance: 62.00,   color: '#7A8450', icon: '💵', trend: [120,100,85,70,62] },
  ],
  recurring: [
    { id: 'r1', merchant: 'Rent · 2BR Oakland',    cat: 'Rent',      amt: -2100, freq: 'monthly', nextRun: 'May 1',  account: 'boa',    lastRun: 'Apr 1',  status: 'active' },
    { id: 'r2', merchant: 'Payroll · Acme Co.',    cat: 'Income',    amt:  2100, freq: 'bi-weekly', nextRun: 'May 3', account: 'boa',  lastRun: 'Apr 18', status: 'active' },
    { id: 'r3', merchant: 'Netflix',               cat: 'Entertain', amt: -15.49, freq: 'monthly', nextRun: 'May 19', account: 'amex', lastRun: 'Apr 19', status: 'active' },
    { id: 'r4', merchant: 'Spotify Family',        cat: 'Entertain', amt: -16.99, freq: 'monthly', nextRun: 'May 7',  account: 'amex', lastRun: 'Apr 7',  status: 'active' },
    { id: 'r5', merchant: 'PG&E Electric',         cat: 'Bills',     amt: -88.20, freq: 'monthly', nextRun: 'May 15', account: 'boa',  lastRun: 'Apr 15', status: 'active' },
    { id: 'r6', merchant: 'iCloud+ 2TB',           cat: 'Bills',     amt:  -9.99, freq: 'monthly', nextRun: 'May 12', account: 'amex', lastRun: 'Apr 12', status: 'paused' },
    { id: 'r7', merchant: 'NYT Digital',           cat: 'Bills',     amt:  -4.00, freq: 'monthly', nextRun: 'May 22', account: 'amex', lastRun: 'Apr 22', status: 'active' },
    { id: 'r8', merchant: 'Auto-save → Chase',     cat: 'Transfer',  amt: -500,   freq: 'monthly', nextRun: 'May 19', account: 'boa',  lastRun: 'Apr 19', status: 'active' },
  ],
  reviewQueue: [
    { id: 'q1', raw: 'alipay_apr_22.png',      merchant: '星巴克 徐家汇店',   amt: -38.00, cat: 'Food',      date: 'Apr 22 · 08:14',  conf: 0.62, reason: 'Merchant new to ledger', suggested: ['Food', 'Other'] },
    { id: 'q2', raw: 'receipt_ikea.jpg',        merchant: 'IKEA Emeryville',  amt: -284.51, cat: 'Shopping',  date: 'Apr 21 · 17:22', conf: 0.71, reason: 'Large amount · no rule match', suggested: ['Shopping','Home'] },
    { id: 'q3', raw: 'wechat_dinner.jpg',       merchant: '炉端烧酒馆',          amt: -156.00, cat: 'Food',      date: 'Apr 21 · 21:03', conf: 0.48, reason: 'Low OCR confidence on amount', suggested: ['Food','Entertain'] },
    { id: 'q4', raw: 'venmo_rent.png',          merchant: 'Kai M. · April rent', amt: -1050.00, cat: 'Rent',     date: 'Apr 20 · 12:00', conf: 0.55, reason: 'Possible transfer not expense', suggested: ['Rent','Transfer'] },
    { id: 'q5', raw: 'uber_apr19.png',          merchant: 'Uber · trip',      amt:  -24.30, cat: 'Transport', date: 'Apr 19 · 23:15', conf: 0.82, reason: 'Category guess only 82%',      suggested: ['Transport'] },
  ],
};

// Small helpers local to new screens
const nsAcctById = (id) => NEW_SAMPLE.accounts.find(a => a.id === id);

function ScreenHeader({ eyebrow, title, children }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', marginBottom: 18, gap: 14 }}>
      <div>
        <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.2, color: 'var(--ink-500)' }}>{eyebrow}</div>
        <h1 className="serif" style={{ fontSize: 28, fontWeight: 500, color: 'var(--ink-900)', letterSpacing: -0.5 }}>{title}</h1>
      </div>
      <div style={{ flex: 1 }} />
      {children}
    </div>
  );
}

// Minimal inline sparkline
function Spark({ data, stroke = 'var(--accent-amber)', w = 120, h = 34, fill }) {
  const min = Math.min(...data), max = Math.max(...data);
  const rng = (max - min) || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / rng) * (h - 4) - 2;
    return [x, y];
  });
  const d = pts.map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` : `L${p[0]},${p[1]}`)).join(' ');
  const a = fill ? `${d} L${w},${h} L0,${h} Z` : '';
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ display: 'block' }}>
      {fill && <path d={a} fill={fill} opacity={0.25}/>}
      <path d={d} fill="none" stroke={stroke} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

// ──────────────────────────────────────────────────────────
// AccountsScreen
// ──────────────────────────────────────────────────────────
function AccountsScreen({ currency }) {
  const [selected, setSelected] = React.useState('boa');
  const cur = nsAcctById(selected);
  const totalAssets = NEW_SAMPLE.accounts.filter(a => a.balance > 0).reduce((s, a) => s + a.balance, 0);
  const totalDebt   = NEW_SAMPLE.accounts.filter(a => a.balance < 0).reduce((s, a) => s + a.balance, 0);
  const net = totalAssets + totalDebt;

  return (
    <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '20px 24px 100px' }}>
      <ScreenHeader eyebrow="Accounts" title="All your money, one ledger">
        <APButton variant="outline" size="md" icon="refresh-ccw">Sync balances</APButton>
        <APButton variant="primary" size="md" icon="plus">Link account</APButton>
      </ScreenHeader>

      {/* Net worth strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
        <PaperCard padding={18}>
          <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1 }}>Net worth</div>
          <div className="serif" style={{ fontSize: 34, fontWeight: 500, color: 'var(--ink-900)', letterSpacing: -0.8, marginTop: 2 }}>
            <Num>{fmtMoney(net, currency)}</Num>
          </div>
          <div style={{ fontSize: 11, color: 'var(--pos-500)', fontWeight: 600, marginTop: 4 }}>+3.2% · last 30d</div>
        </PaperCard>
        <PaperCard padding={18}>
          <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1 }}>Assets</div>
          <div className="serif" style={{ fontSize: 28, fontWeight: 500, color: 'var(--pos-500)', marginTop: 2 }}>
            <Num>{fmtMoney(totalAssets, currency)}</Num>
          </div>
          <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 4 }}>across 4 accounts</div>
        </PaperCard>
        <PaperCard padding={18}>
          <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1 }}>Liabilities</div>
          <div className="serif" style={{ fontSize: 28, fontWeight: 500, color: 'var(--neg-500)', marginTop: 2 }}>
            <Num>{fmtMoney(totalDebt, currency)}</Num>
          </div>
          <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 4 }}>1 credit card</div>
        </PaperCard>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: 16 }}>
        {/* Account list */}
        <PaperCard padding={0}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center' }}>
            <div style={{ fontSize: 13.5, fontWeight: 600 }}>Your accounts</div>
            <div style={{ flex: 1 }}/>
            <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>{NEW_SAMPLE.accounts.length} total</div>
          </div>
          {NEW_SAMPLE.accounts.map((a, i) => {
            const on = selected === a.id;
            const isDebt = a.balance < 0;
            return (
              <button key={a.id} onClick={() => setSelected(a.id)} style={{
                display: 'grid', gridTemplateColumns: '36px 1fr auto', gap: 12, alignItems: 'center',
                padding: '14px 18px', width: '100%', border: 'none', textAlign: 'left', cursor: 'pointer',
                borderBottom: i < NEW_SAMPLE.accounts.length - 1 ? '1px solid var(--ink-100)' : 'none',
                background: on ? 'var(--cream-200)' : 'transparent',
                borderLeft: on ? '3px solid var(--ink-900)' : '3px solid transparent',
                fontFamily: 'var(--font-ui)',
              }}>
                <div style={{ width: 34, height: 34, borderRadius: 9, background: 'var(--cream-100)', border: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 17 }}>{a.icon}</div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{a.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 0.7 }}>{a.kind} · ··{a.last4}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="num" style={{ fontSize: 14, fontWeight: 700, color: isDebt ? 'var(--neg-500)' : 'var(--ink-900)' }}>
                    {fmtMoney(a.balance, currency)}
                  </div>
                  {a.limit && <div style={{ fontSize: 10.5, color: 'var(--ink-500)' }}>of {fmtMoney(a.limit, currency)}</div>}
                </div>
              </button>
            );
          })}
          <div style={{ padding: 14 }}>
            <button style={{
              width: '100%', padding: '10px', borderRadius: 9, background: 'transparent',
              border: '1.5px dashed var(--ink-300)', color: 'var(--ink-500)', fontSize: 12.5,
              fontFamily: 'var(--font-ui)', cursor: 'pointer', fontWeight: 600,
            }}>+ Add manual account</button>
          </div>
        </PaperCard>

        {/* Detail */}
        <PaperCard padding={0}>
          <div style={{ padding: 18, borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ width: 52, height: 52, borderRadius: 12, background: cur.color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, color: '#fff' }}>{cur.icon}</div>
            <div style={{ flex: 1 }}>
              <div className="serif" style={{ fontSize: 20, fontWeight: 500, color: 'var(--ink-900)' }}>{cur.name}</div>
              <div style={{ fontSize: 11.5, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 0.8 }}>{cur.kind} · ending ··{cur.last4}</div>
            </div>
            <APButton variant="outline" size="sm" icon="pencil">Edit</APButton>
          </div>

          <div style={{ padding: 18, display: 'grid', gridTemplateColumns: '1fr 140px', gap: 16, alignItems: 'center', borderBottom: '1px solid var(--ink-100)' }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1 }}>
                {cur.balance < 0 ? 'Current balance owed' : 'Available balance'}
              </div>
              <div className="serif" style={{ fontSize: 36, fontWeight: 500, color: cur.balance < 0 ? 'var(--neg-500)' : 'var(--ink-900)', letterSpacing: -0.6 }}>
                <Num>{fmtMoney(cur.balance, currency)}</Num>
              </div>
              <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>Synced 4 min ago</div>
            </div>
            <div style={{ padding: 8, background: 'var(--cream-100)', borderRadius: 9, border: '1px solid var(--ink-200)' }}>
              <div style={{ fontSize: 10, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 2 }}>5-mo trend</div>
              <Spark data={cur.trend} stroke={cur.color} w={120} h={40} fill={cur.color}/>
            </div>
          </div>

          {/* Quick actions */}
          <div style={{ padding: 16, display: 'flex', gap: 8, borderBottom: '1px solid var(--ink-100)' }}>
            <APButton variant="secondary" size="sm" icon="arrow-right">Transfer</APButton>
            <APButton variant="secondary" size="sm" icon="refresh-ccw">Reconcile</APButton>
            <APButton variant="secondary" size="sm" icon="download">Export</APButton>
            <div style={{ flex: 1 }}/>
            <APButton variant="ghost" size="sm" icon="ellipsis">More</APButton>
          </div>

          {/* Recent activity */}
          <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--ink-200)' }}>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink-900)' }}>Recent activity on this account</div>
          </div>
          {SAMPLE.transactions.slice(0, 5).map((t, i, arr) => (
            <div key={t.id} style={{ display: 'grid', gridTemplateColumns: '60px 1fr 110px 100px', gap: 10, alignItems: 'center', padding: '10px 18px', fontSize: 12.5, borderBottom: i < arr.length - 1 ? '1px solid var(--ink-100)' : 'none' }}>
              <div style={{ color: 'var(--ink-500)', fontSize: 11 }}>{t.date}</div>
              <div style={{ color: 'var(--ink-900)', fontWeight: 500 }}>{t.merchant}</div>
              <CatPill cat={t.cat} size="sm"/>
              <div className="num" style={{ textAlign: 'right', fontWeight: 700, color: t.amt > 0 ? 'var(--pos-500)' : 'var(--ink-900)' }}>
                {t.amt > 0 ? '+' : ''}{fmtMoney(t.amt, currency)}
              </div>
            </div>
          ))}
        </PaperCard>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────
// RecurringScreen
// ──────────────────────────────────────────────────────────
function RecurringScreen({ currency }) {
  const [filter, setFilter] = React.useState('all');
  const rows = NEW_SAMPLE.recurring.filter(r =>
    filter === 'all' ? true : filter === 'paused' ? r.status === 'paused' :
    filter === 'income' ? r.amt > 0 : filter === 'transfer' ? r.cat === 'Transfer' : r.amt < 0 && r.cat !== 'Transfer'
  );
  const monthlyOut = NEW_SAMPLE.recurring.filter(r => r.status === 'active' && r.amt < 0).reduce((s, r) => s + r.amt, 0);
  const monthlyIn  = NEW_SAMPLE.recurring.filter(r => r.status === 'active' && r.amt > 0).reduce((s, r) => s + r.amt, 0);

  return (
    <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '20px 24px 100px' }}>
      <ScreenHeader eyebrow="Recurring" title="Bills, subscriptions & auto-saves">
        <APButton variant="outline" size="md" icon="sparkles">Auto-detect from history</APButton>
        <APButton variant="primary" size="md" icon="plus">New rule</APButton>
      </ScreenHeader>

      {/* summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
        <PaperCard padding={18}>
          <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1 }}>Monthly outflow</div>
          <div className="serif" style={{ fontSize: 30, fontWeight: 500, color: 'var(--neg-500)', marginTop: 2 }}>
            <Num>{fmtMoney(Math.abs(monthlyOut), currency)}</Num>
          </div>
          <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>7 active rules</div>
        </PaperCard>
        <PaperCard padding={18}>
          <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1 }}>Monthly inflow</div>
          <div className="serif" style={{ fontSize: 30, fontWeight: 500, color: 'var(--pos-500)', marginTop: 2 }}>
            <Num>{fmtMoney(monthlyIn, currency)}</Num>
          </div>
          <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>1 active salary rule</div>
        </PaperCard>
        <PaperCard padding={18}>
          <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1 }}>Next 7 days</div>
          <div className="serif" style={{ fontSize: 30, fontWeight: 500, color: 'var(--ink-900)', marginTop: 2 }}>3 charges</div>
          <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>Rent · Spotify · Netflix</div>
        </PaperCard>
      </div>

      <PaperCard padding={0}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <SegmentedToggle
            options={[
              {id:'all',label:'All'},{id:'bill',label:'Bills'},
              {id:'income',label:'Income'},{id:'transfer',label:'Transfers'},{id:'paused',label:'Paused'},
            ]}
            value={filter} onChange={setFilter}/>
          <div style={{ flex: 1 }}/>
          <APButton variant="ghost" size="sm" icon="clock">Upcoming only</APButton>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '40px 1fr 110px 110px 130px 110px 36px', padding: '8px 18px', gap: 12, fontSize: 10.5, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--ink-500)', fontWeight: 600, background: 'var(--cream-100)', borderBottom: '1px solid var(--ink-200)' }}>
          <span>Status</span><span>Merchant · account</span><span>Category</span><span>Frequency</span><span>Next run</span><span style={{ textAlign: 'right' }}>Amount</span><span/>
        </div>

        {rows.map((r, i) => {
          const acct = nsAcctById(r.account);
          const paused = r.status === 'paused';
          return (
            <div key={r.id} style={{ display: 'grid', gridTemplateColumns: '40px 1fr 110px 110px 130px 110px 36px', padding: '12px 18px', gap: 12, alignItems: 'center', borderBottom: i < rows.length - 1 ? '1px solid var(--ink-100)' : 'none', opacity: paused ? 0.55 : 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{
                  width: 10, height: 10, borderRadius: 5,
                  background: paused ? 'var(--ink-300)' : (r.amt > 0 ? 'var(--pos-500)' : 'var(--accent-amber)'),
                }}/>
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>{r.merchant}</div>
                <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>{acct.icon} {acct.name}</div>
              </div>
              <CatPill cat={r.cat === 'Transfer' ? 'Other' : r.cat} size="sm"/>
              <div style={{ fontSize: 12, color: 'var(--ink-700)', textTransform: 'capitalize' }}>{r.freq}</div>
              <div style={{ fontSize: 12, color: 'var(--ink-900)', fontWeight: 600 }}>
                {paused ? '— paused —' : r.nextRun}
                {!paused && <div style={{ fontSize: 10.5, color: 'var(--ink-500)', fontWeight: 400 }}>last: {r.lastRun}</div>}
              </div>
              <div className="num" style={{ textAlign: 'right', fontWeight: 700, color: r.amt > 0 ? 'var(--pos-500)' : 'var(--ink-900)' }}>
                {r.amt > 0 ? '+' : ''}{fmtMoney(r.amt, currency)}
              </div>
              <button style={{ border: 'none', background: 'transparent', color: 'var(--ink-400)', cursor: 'pointer', width: 28, height: 28, borderRadius: 6 }}>
                <Icon name="ellipsis" size={14}/>
              </button>
            </div>
          );
        })}

        <div style={{ padding: '12px 18px', background: 'var(--cream-100)', borderTop: '1px solid var(--ink-200)', fontSize: 11.5, color: 'var(--ink-500)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Icon name="sparkles" size={14}/>
          MITA detected <strong style={{ color: 'var(--ink-900)' }}>2 new candidates</strong> in your recent records — "Claude Pro $20/mo" and "Cursor $20/mo".
          <div style={{ flex: 1 }}/>
          <APButton variant="outline" size="sm">Review →</APButton>
        </div>
      </PaperCard>
    </div>
  );
}

// ──────────────────────────────────────────────────────────
// ReviewQueueScreen
// ──────────────────────────────────────────────────────────
function ReviewQueueScreen({ currency }) {
  const [idx, setIdx] = React.useState(0);
  const items = NEW_SAMPLE.reviewQueue;
  const cur = items[idx];
  const approve = () => setIdx(i => Math.min(i + 1, items.length - 1));

  return (
    <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '20px 24px 100px' }}>
      <ScreenHeader eyebrow="Review queue" title="Tell MITA what these are">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginRight: 6, fontSize: 12, color: 'var(--ink-500)' }}>
          <span className="num" style={{ fontWeight: 700, color: 'var(--ink-900)' }}>{idx + 1}</span> of {items.length} pending
        </div>
        <APButton variant="outline" size="md" icon="check">Approve all</APButton>
      </ScreenHeader>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 16 }}>
        {/* Queue list */}
        <PaperCard padding={0}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--ink-200)', fontSize: 12.5, fontWeight: 600 }}>
            Awaiting you
          </div>
          {items.map((it, i) => {
            const on = i === idx;
            const conf = Math.round(it.conf * 100);
            return (
              <button key={it.id} onClick={() => setIdx(i)} style={{
                display: 'block', width: '100%', textAlign: 'left', padding: '12px 16px',
                border: 'none', cursor: 'pointer',
                background: on ? 'var(--cream-200)' : 'transparent',
                borderLeft: on ? '3px solid var(--accent-amber)' : '3px solid transparent',
                borderBottom: i < items.length - 1 ? '1px solid var(--ink-100)' : 'none',
                fontFamily: 'var(--font-ui)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)', flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{it.merchant}</div>
                  <span className="num" style={{ fontSize: 12, color: 'var(--neg-500)', fontWeight: 700 }}>{fmtMoney(it.amt, currency)}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                  <div style={{ width: 36, height: 4, borderRadius: 2, background: 'var(--cream-300)', overflow: 'hidden' }}>
                    <div style={{ width: `${conf}%`, height: '100%', background: conf < 60 ? 'var(--neg-500)' : conf < 80 ? 'var(--accent-amber)' : 'var(--pos-500)' }}/>
                  </div>
                  <span style={{ fontSize: 10.5, color: 'var(--ink-500)' }}>{conf}% sure</span>
                  <div style={{ flex: 1 }}/>
                  <span style={{ fontSize: 10.5, color: 'var(--ink-500)' }}>{it.date.split('·')[0]}</span>
                </div>
              </button>
            );
          })}
        </PaperCard>

        {/* Detail / edit */}
        <PaperCard padding={0}>
          <div style={{ padding: 18, borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'flex-start', gap: 14 }}>
            <div style={{ width: 80, height: 100, borderRadius: 9, background: 'var(--cream-200)', border: '1px dashed var(--ink-300)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-400)', fontSize: 11, textAlign: 'center', padding: 6 }}>
              <div><Icon name="image" size={22}/><div style={{ marginTop: 4 }}>{cur.raw}</div></div>
            </div>
            <div style={{ flex: 1 }}>
              <div className="serif" style={{ fontSize: 22, fontWeight: 500, color: 'var(--ink-900)' }}>{cur.merchant}</div>
              <div style={{ fontSize: 12.5, color: 'var(--ink-500)' }}>{cur.date}</div>
              <div style={{ marginTop: 8, display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 9999, background: 'var(--cream-100)', border: '1px solid var(--ink-200)', fontSize: 11, color: 'var(--ink-700)' }}>
                <Icon name="sparkles" size={12}/>
                <span><strong style={{ color: 'var(--ink-900)' }}>Why flagged:</strong> {cur.reason}</span>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="serif num" style={{ fontSize: 34, fontWeight: 500, color: 'var(--neg-500)', letterSpacing: -0.5 }}>
                {fmtMoney(cur.amt, currency)}
              </div>
              <div style={{ fontSize: 10.5, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1 }}>amount · editable</div>
            </div>
          </div>

          {/* Agent suggestion */}
          <div style={{ padding: 18, borderBottom: '1px solid var(--ink-200)', background: 'var(--cream-100)' }}>
            <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Icon name="sparkles" size={12}/> MITA's guess
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <CatPill cat={cur.cat}/>
              <span style={{ fontSize: 12, color: 'var(--ink-500)' }}>{Math.round(cur.conf * 100)}% confident</span>
              <div style={{ flex: 1 }}/>
              <span style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>Alternatives:</span>
              {cur.suggested.filter(s => s !== cur.cat).map(s => (
                <button key={s} style={{ padding: '4px 10px', borderRadius: 9999, background: 'var(--cream-50)', border: '1px solid var(--ink-200)', fontSize: 11, cursor: 'pointer', fontFamily: 'var(--font-ui)', color: 'var(--ink-700)' }}>{s}</button>
              ))}
            </div>
          </div>

          {/* Edit grid */}
          <div style={{ padding: 18, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <ManualField label="Merchant" placeholder={cur.merchant}/>
            <ManualField label="Amount" placeholder={Math.abs(cur.amt).toString()} icon={SYM[currency]}/>
            <ManualField label="Date" placeholder={cur.date}/>
            <div>
              <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 5 }}>Account</div>
              <select style={{ height: 36, width: '100%', padding: '0 11px', borderRadius: 9, border: '1px solid var(--ink-200)', background: 'var(--cream-50)', fontSize: 13, fontFamily: 'var(--font-ui)' }}>
                {NEW_SAMPLE.accounts.map(a => <option key={a.id}>{a.icon} {a.name}</option>)}
              </select>
            </div>
            <div style={{ gridColumn: '1/-1' }}>
              <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 5 }}>Category</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {Object.keys(CAT_COLORS).map(c => (
                  <div key={c} style={{ opacity: c === cur.cat ? 1 : 0.55, transform: c === cur.cat ? 'scale(1.05)' : 'none', transition: 'all 120ms' }}>
                    <CatPill cat={c}/>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Action bar */}
          <div style={{ padding: '14px 18px', borderTop: '1px solid var(--ink-200)', background: 'var(--cream-100)', display: 'flex', alignItems: 'center', gap: 10 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--ink-700)' }}>
              <input type="checkbox" defaultChecked style={{ accentColor: 'var(--accent-amber)' }}/>
              Teach MITA: always categorize "{cur.merchant.split(' ')[0]}" as {cur.cat}
            </label>
            <div style={{ flex: 1 }}/>
            <APButton variant="ghost" size="sm">Reject</APButton>
            <APButton variant="outline" size="sm" icon="pencil">Edit & save</APButton>
            <APButton variant="primary" size="sm" icon="check" onClick={approve}>Approve</APButton>
          </div>
        </PaperCard>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────
// BudgetScreenV2 — richer per-category budgets, status pills,
// overspend warning, month progress, savings goals
// ──────────────────────────────────────────────────────────
function BudgetScreenV2({ currency }) {
  const { t } = useT();
  // Per-category budgets (mo USD) vs actual this month
  const budgets = [
    { cat: 'Food',       spent: 412, cap: 450 },
    { cat: 'Rent',       spent: 2100, cap: 2100 },
    { cat: 'Transport',  spent: 148, cap: 180 },
    { cat: 'Shopping',   spent: 186, cap: 150 }, // over
    { cat: 'Bills',      spent: 128, cap: 200 },
    { cat: 'Entertain',  spent:  91, cap:  80 }, // over
    { cat: 'Health',     spent:  24, cap: 100 },
  ];
  const monthDay = 22, monthDays = 30;
  const monthProgress = (monthDay / monthDays) * 100;
  const totalSpent = budgets.reduce((s, b) => s + b.spent, 0);
  const totalCap   = budgets.reduce((s, b) => s + b.cap, 0);

  return (
    <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '20px 24px 100px' }}>
      <ScreenHeader eyebrow="Budget & goals" title="Tell MITA what you're aiming for">
        <APButton variant="outline" size="md" icon="refresh-ccw">Copy last month</APButton>
        <APButton variant="primary" size="md" icon="plus">New budget</APButton>
      </ScreenHeader>

      {/* Monthly summary banner */}
      <PaperCard padding={20} style={{ marginBottom: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 20, alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1 }}>Spent this month</div>
            <div className="serif num" style={{ fontSize: 32, fontWeight: 500, color: 'var(--ink-900)', letterSpacing: -0.5 }}>{fmtMoney(totalSpent, currency)}</div>
            <div style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>of <Num>{fmtMoney(totalCap, currency)}</Num> budgeted</div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1 }}>Month progress</div>
            <div className="serif num" style={{ fontSize: 32, fontWeight: 500, color: 'var(--ink-900)' }}>{monthDay}<span style={{ color: 'var(--ink-500)' }}> / {monthDays}</span></div>
            <div style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>days · 8 left</div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1 }}>Remaining</div>
            <div className="serif num" style={{ fontSize: 32, fontWeight: 500, color: 'var(--pos-500)' }}>{fmtMoney(totalCap - totalSpent, currency)}</div>
            <div style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>~<Num>{fmtMoney((totalCap-totalSpent)/(monthDays-monthDay), currency)}</Num>/day left</div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1 }}>On-pace score</div>
            <div className="serif" style={{ fontSize: 32, fontWeight: 500, color: 'var(--accent-amber)' }}>B+</div>
            <div style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>2 categories over</div>
          </div>
        </div>

        {/* Big progress bar with month-marker */}
        <div style={{ marginTop: 18, position: 'relative' }}>
          <div style={{ height: 10, background: 'var(--cream-200)', borderRadius: 5, overflow: 'hidden' }}>
            <div style={{ width: `${(totalSpent/totalCap)*100}%`, height: '100%', background: 'linear-gradient(90deg, var(--cream-400), var(--accent-amber))' }}/>
          </div>
          <div style={{ position: 'absolute', top: -4, left: `calc(${monthProgress}% - 1px)`, width: 2, height: 18, background: 'var(--ink-900)' }}/>
          <div style={{ position: 'absolute', top: 20, left: `calc(${monthProgress}% - 30px)`, fontSize: 10.5, color: 'var(--ink-500)', fontWeight: 600 }}>today ({Math.round(monthProgress)}%)</div>
        </div>
      </PaperCard>

      {/* Per-category budgets */}
      <PaperCard padding={0} style={{ marginBottom: 16 }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 13.5, fontWeight: 600 }}>Per-category budgets</div>
            <div style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>MITA warns you at 80% and again at 100%</div>
          </div>
          <div style={{ flex: 1 }}/>
          <APButton variant="outline" size="sm" icon="plus">Add category</APButton>
        </div>

        {budgets.map((b, i) => {
          const pct = (b.spent / b.cap) * 100;
          const over = b.spent > b.cap;
          const near = !over && pct > 80;
          const col = CAT_COLORS[b.cat].dot;
          const badge = over ? { bg:'#F5E6DE', fg:'var(--neg-500)', text:`${Math.round(pct-100)}% over` } : near ? { bg:'#FCE5CE', fg:'var(--accent-amber)', text:`${Math.round(pct)}%` } : { bg:'#E6F2EA', fg:'var(--pos-500)', text:`on pace` };
          return (
            <div key={b.cat} style={{ padding: '14px 18px', display: 'grid', gridTemplateColumns: '130px 1fr 90px 90px 110px 36px', gap: 14, alignItems: 'center', borderBottom: i < budgets.length - 1 ? '1px solid var(--ink-100)' : 'none' }}>
              <CatPill cat={b.cat}/>
              <div>
                <div style={{ height: 7, background: 'var(--cream-200)', borderRadius: 4, overflow: 'hidden', position: 'relative' }}>
                  <div style={{ width: `${Math.min(pct, 100)}%`, height: '100%', background: over ? 'var(--neg-500)' : col }}/>
                  {over && (
                    <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(255,255,255,.35) 4px, rgba(255,255,255,.35) 8px)', pointerEvents:'none' }}/>
                  )}
                </div>
                <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 5 }}>
                  <strong style={{ color: 'var(--ink-900)' }} className="num">{fmtMoney(b.spent, currency)}</strong>
                  {' of '}<Num>{fmtMoney(b.cap, currency)}</Num>
                </div>
              </div>
              <span style={{ fontSize: 10.5, padding: '4px 8px', borderRadius: 9999, background: badge.bg, color: badge.fg, fontWeight: 700, justifySelf: 'center' }}>{badge.text}</span>
              <div className="num" style={{ fontSize: 12, color: over ? 'var(--neg-500)' : 'var(--ink-500)', textAlign: 'right', fontWeight: 600 }}>
                {over ? '−' : ''}{fmtMoney(Math.abs(b.cap - b.spent), currency)}
              </div>
              <button style={{ border: '1px solid var(--ink-200)', background: 'var(--cream-50)', borderRadius: 7, padding: '5px 10px', fontSize: 11.5, cursor: 'pointer', fontFamily: 'var(--font-ui)' }}>Edit cap</button>
              <button style={{ border: 'none', background: 'transparent', color: 'var(--ink-400)', cursor: 'pointer' }}><Icon name="ellipsis" size={14}/></button>
            </div>
          );
        })}
      </PaperCard>

      {/* Savings goals */}
      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-900)', marginBottom: 10 }}>Savings goals</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        {[
          { emoji: '✈', title: 'Kyoto trip', current: 1240, target: 2400, due: 'Jun 15' },
          { emoji: '💻', title: 'New laptop', current: 820, target: 1800, due: 'Aug 1' },
          { emoji: '🏔', title: 'Emergency fund', current: 4200, target: 6000, due: 'Dec 31' },
        ].map(g => {
          const pct = Math.round(g.current/g.target*100);
          return (
            <PaperCard key={g.title} padding={18}>
              <div style={{ fontSize: 22 }}>{g.emoji}</div>
              <div className="serif" style={{ fontSize: 18, fontWeight: 500, color: 'var(--ink-900)', marginTop: 4 }}>{g.title}</div>
              <div style={{ fontSize: 11.5, color: 'var(--ink-500)', marginBottom: 10 }}>by {g.due}</div>
              <div style={{ height: 8, background: 'var(--cream-200)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: 'var(--pos-500)' }}/>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 12 }}>
                <span className="num" style={{ color: 'var(--ink-900)', fontWeight: 600 }}>{fmtMoney(g.current, currency)}</span>
                <span style={{ color: 'var(--ink-500)' }}>of <Num>{fmtMoney(g.target, currency)}</Num> · {pct}%</span>
              </div>
            </PaperCard>
          );
        })}
      </div>
    </div>
  );
}

Object.assign(window, { AccountsScreen, RecurringScreen, ReviewQueueScreen, BudgetScreenV2 });
