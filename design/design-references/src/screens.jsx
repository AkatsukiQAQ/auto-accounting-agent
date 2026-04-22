// Supporting screens: Records detail, Import, Budget/Settings, Categories

function RecordsScreen({ currency }) {
  const { t, lang } = useT();
  const [filter, setFilter] = React.useState('all');
  const [search, setSearch] = React.useState('');
  const rows = SAMPLE.transactions.filter(t => {
    if (filter === 'income' && t.amt <= 0) return false;
    if (filter === 'expense' && t.amt > 0) return false;
    if (search && !t.merchant.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '20px 24px 100px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', marginBottom: 18, gap: 14 }}>
        <div>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.2, color: 'var(--ink-500)' }}>{t('records_header_title')}</div>
          <h1 className="serif" style={{ fontSize: 28, fontWeight: 500, color: 'var(--ink-900)', letterSpacing: -0.5 }}>{t('records_header_sub')}</h1>
        </div>
        <div style={{ flex: 1 }} />
        <APButton variant="outline" size="md" icon="download">{t('export_csv')}</APButton>
        <APButton variant="outline" size="md" icon="download">{t('export_json')}</APButton>
        <APButton variant="primary" size="md" icon="plus">Add</APButton>
      </div>

      <PaperCard padding={0}>
        {/* Toolbar */}
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, height: 34, padding: '0 12px',
            borderRadius: 9, border: '1px solid var(--ink-200)', background: 'var(--cream-100)', width: 260,
          }}>
            <Icon name="search" size={14} />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search merchants, notes…"
              style={{ flex: 1, border: 'none', background: 'transparent', outline: 'none', fontSize: 13, color: 'var(--ink-900)', fontFamily: 'var(--font-sans)' }} />
          </div>
          <SegmentedToggle
            options={[{id:'all',label:'All'},{id:'expense',label:'Expense'},{id:'income',label:'Income'}]}
            value={filter} onChange={setFilter} />
          <div style={{ flex: 1 }} />
          <APButton variant="ghost" size="sm" icon="folder">{t('category')}</APButton>
          <APButton variant="ghost" size="sm" icon="clock">{t('date_range')}</APButton>
          <APButton variant="ghost" size="sm" icon="ellipsis" />
        </div>

        {/* Table header */}
        <div style={{
          display: 'grid', gridTemplateColumns: '20px 76px 1fr 110px 110px 100px 36px',
          padding: '8px 18px', gap: 12,
          fontSize: 10.5, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--ink-500)', fontWeight: 600,
          background: 'var(--cream-100)', borderBottom: '1px solid var(--ink-200)',
        }}>
          <span/><span>Date</span><span>Merchant / Note</span><span>{t('category')}</span><span>Source</span><span style={{ textAlign: 'right' }}>Amount</span><span/>
        </div>

        {rows.map((t, i) => (
          <div key={t.id} style={{
            display: 'grid', gridTemplateColumns: '20px 76px 1fr 110px 110px 100px 36px',
            padding: '12px 18px', gap: 12, alignItems: 'center', fontSize: 13,
            borderBottom: i < rows.length - 1 ? '1px solid var(--ink-100)' : 'none',
            transition: 'background 120ms',
          }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--cream-100)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
            <input type="checkbox" style={{ accentColor: 'var(--accent-amber)' }}/>
            <div style={{ color: 'var(--ink-700)', fontSize: 11.5 }}>
              <div style={{ fontWeight: 600, color: 'var(--ink-900)', fontSize: 12 }}>{t.date}</div>{t.time}
            </div>
            <div>
              <div style={{ color: 'var(--ink-900)', fontWeight: 500 }}>{t.merchant}</div>
              {t.note && <div style={{ fontSize: 11.5, color: 'var(--ink-500)', fontStyle: 'italic', marginTop: 1 }}>{t.note}</div>}
            </div>
            <CatPill cat={t.cat} size="sm" />
            <SourceTag src={t.src} />
            <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 600, color: t.amt > 0 ? 'var(--pos-500)' : 'var(--ink-900)' }}>
              {t.amt > 0 ? '+' : ''}{fmtMoney(t.amt, currency)}
            </div>
            <button style={{ border: 'none', background: 'transparent', color: 'var(--ink-400)', cursor: 'pointer', width: 28, height: 28, borderRadius: 6 }}>
              <Icon name="ellipsis" size={14} />
            </button>
          </div>
        ))}

        {/* Footer summary */}
        <div style={{ padding: '12px 18px', borderTop: '1px solid var(--ink-200)', background: 'var(--cream-100)', display: 'flex', gap: 18, fontSize: 12, color: 'var(--ink-500)' }}>
          <span>Showing <strong style={{ color: 'var(--ink-900)' }}>{rows.length}</strong> of {SAMPLE.transactions.length}</span>
          <span>Total expense <strong style={{ color: 'var(--neg-500)' }}>{fmtMoney(Math.abs(rows.filter(r=>r.amt<0).reduce((a,r)=>a+r.amt,0)), currency)}</strong></span>
          <span>Total income <strong style={{ color: 'var(--pos-500)' }}>{fmtMoney(rows.filter(r=>r.amt>0).reduce((a,r)=>a+r.amt,0), currency)}</strong></span>
        </div>
      </PaperCard>
    </div>
  );
}

function ImportScreen({ currency }) {
  const { t, lang } = useT();
  const [mode, setMode] = React.useState('screenshot');
  const [dragOver, setDragOver] = React.useState(false);

  return (
    <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '20px 24px 100px' }}>
      <div style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.2, color: 'var(--ink-500)' }}>{t('import_eyebrow')}</div>
        <h1 className="serif" style={{ fontSize: 28, fontWeight: 500, color: 'var(--ink-900)', letterSpacing: -0.5 }}>{t('import_title')}</h1>
      </div>

      <SegmentedToggle
        options={[{id:'screenshot',label:'Screenshot'},{id:'manual',label:'Manual'},{id:'csv',label:'CSV / Bank'}]}
        value={mode} onChange={setMode} />

      <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 16 }}>
        {mode === 'screenshot' && (
          <PaperCard padding={0}>
            <div
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={e => { e.preventDefault(); setDragOver(false); }}
              style={{
                border: `2px dashed ${dragOver ? 'var(--accent-amber)' : 'var(--ink-300)'}`,
                borderRadius: 12, margin: 16, padding: 40,
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                background: dragOver ? 'var(--cream-200)' : 'var(--cream-100)', textAlign: 'center',
                transition: 'all 150ms var(--ease)', minHeight: 280,
              }}>
              <div style={{
                width: 56, height: 56, borderRadius: 14, background: 'var(--cream-300)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14,
              }}>
                <Icon name="upload" size={24} />
              </div>
              <div className="serif" style={{ fontSize: 20, fontWeight: 500, color: 'var(--ink-900)', marginBottom: 4 }}>{t('drop_here')}</div>
              <div style={{ fontSize: 12.5, color: 'var(--ink-500)', marginBottom: 16 }}>
                Alipay, WeChat Pay, Venmo, receipts — anything with text. PNG or JPG.
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <APButton variant="primary" size="md" icon="upload">{t('choose_file')}</APButton>
                <APButton variant="outline" size="md" icon="paperclip">{t('paste_clip')}</APButton>
              </div>
              <div style={{ marginTop: 16, fontSize: 11, color: 'var(--ink-400)' }}>MITA OCRs → extracts → classifies, all on-device.</div>
            </div>

            {/* Queue */}
            <div style={{ padding: '0 16px 16px' }}>
              <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>{t('processing_queue')}</div>
              {[
                { name: 'alipay_apr_21.png', status: 'done',    result: '7 records extracted' },
                { name: 'wechat_lunch.jpg', status: 'review',   result: 'Needs category confirmation' },
                { name: 'venmo_split.png',  status: 'working',  result: 'Running OCR…' },
              ].map((f, i) => {
                const sc = { done: 'var(--pos-500)', review: 'var(--accent-amber)', working: 'var(--info-500)' }[f.status];
                return (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 10, borderRadius: 9, border: '1px solid var(--ink-200)', marginBottom: 6, background: 'var(--cream-50)' }}>
                    <div style={{ width: 36, height: 36, borderRadius: 7, background: 'var(--cream-200)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Icon name="image" size={16}/>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12.5, fontWeight: 500, color: 'var(--ink-900)' }}>{f.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>{f.result}</div>
                    </div>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, fontWeight: 600, color: sc, padding: '3px 8px', borderRadius: 9999, background: 'var(--cream-100)', border: `1px solid ${sc}` }}>
                      <span style={{ width: 6, height: 6, borderRadius: 3, background: sc }}/>
                      {f.status}
                    </span>
                  </div>
                );
              })}
            </div>
          </PaperCard>
        )}

        {mode === 'manual' && (
          <PaperCard padding={20}>
            <div className="serif" style={{ fontSize: 18, fontWeight: 600, color: 'var(--ink-900)', marginBottom: 12 }}>{t('manual_entry')}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <ManualField label="Merchant / Description" placeholder="e.g. Blue Bottle Coffee" />
              <ManualField label="Amount" placeholder="7.25" icon={SYM[currency]} />
              <ManualField label="Date" placeholder="Apr 21, 2026" icon="📅" />
              <ManualField label="Time" placeholder="12:34" icon="⏱" />
              <div style={{ gridColumn: '1/-1' }}>
                <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--ink-700)', marginBottom: 5 }}>{t('category')}</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {Object.keys(CAT_COLORS).map(c => <CatPill key={c} cat={c}/>)}
                </div>
              </div>
              <ManualField label="Note (optional)" placeholder="Oat latte, AM standup" span={2} />
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <APButton variant="primary" size="md">{t('save_record')}</APButton>
              <APButton variant="outline" size="md">Save &amp; add another</APButton>
            </div>
          </PaperCard>
        )}

        {mode === 'csv' && (
          <PaperCard padding={20}>
            <div className="serif" style={{ fontSize: 18, fontWeight: 600, color: 'var(--ink-900)', marginBottom: 6 }}>{t('bulk_import')}</div>
            <div style={{ fontSize: 12.5, color: 'var(--ink-500)', marginBottom: 14 }}>Upload a CSV, OFX, or connect a bank. MITA will de-duplicate against existing records.</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {['Chase · checking', 'Mercury · savings', 'PayPal', 'Alipay export'].map((n, i) => (
                <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 9, border: '1px solid var(--ink-200)' }}>
                  <div style={{ width: 30, height: 30, borderRadius: 7, background: 'var(--cream-200)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Icon name="link" size={14}/>
                  </div>
                  <div style={{ flex: 1, fontSize: 13, color: 'var(--ink-900)' }}>{n}</div>
                  <APButton variant={i === 0 ? 'secondary' : 'outline'} size="sm">{i === 0 ? 'Connected' : 'Connect'}</APButton>
                </div>
              ))}
            </div>
          </PaperCard>
        )}

        {/* Tips */}
        <PaperCard padding={20}>
          <div className="hand" style={{ fontSize: 20, color: 'var(--ink-900)', marginBottom: 8 }}>{t('tips')}</div>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, lineHeight: 1.75, color: 'var(--ink-700)' }}>
            <li>Screenshots work best on <strong>one receipt at a time</strong> — a clear 500px+ wide crop.</li>
            <li>{t('tips_dark_ok')}</li>
            <li>I'll ask before saving anything that looks ambiguous (duplicate, unknown currency).</li>
            <li>Amounts are auto-converted to your preferred display currency.</li>
          </ul>
          <div style={{ marginTop: 14, padding: 12, background: 'var(--cream-100)', borderRadius: 9, border: '1px dashed var(--cream-400)' }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent-amber)', textTransform: 'uppercase', letterSpacing: 1 }}>{t('last_30')}</div>
            <div className="serif" style={{ fontSize: 22, fontWeight: 500, color: 'var(--ink-900)', marginTop: 2 }}>184 screenshots · 2 misses</div>
            <div style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>98.9% parse accuracy</div>
          </div>
        </PaperCard>
      </div>
    </div>
  );
}

function ManualField({ label, placeholder, icon, span = 1 }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 5, gridColumn: span === 2 ? '1/-1' : undefined }}>
      <span style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--ink-700)' }}>{label}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, height: 36, padding: '0 11px', borderRadius: 9, border: '1px solid var(--ink-200)', background: 'var(--cream-50)' }}>
        {icon && <span style={{ color: 'var(--ink-400)', fontSize: 13 }}>{icon}</span>}
        <input placeholder={placeholder} style={{ flex: 1, border: 'none', background: 'transparent', outline: 'none', fontSize: 13, color: 'var(--ink-900)', fontFamily: 'var(--font-sans)' }}/>
      </div>
    </label>
  );
}

function BudgetScreen({ currency }) {
  const { t, lang } = useT();
  return (
    <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '20px 24px 100px' }}>
      <div style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.2, color: 'var(--ink-500)' }}>Budget &amp; goals</div>
        <h1 className="serif" style={{ fontSize: 28, fontWeight: 500, color: 'var(--ink-900)', letterSpacing: -0.5 }}>{t('budget_title')}</h1>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        <PaperCard padding={20}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-900)', marginBottom: 4 }}>{t('monthly_spend_cap')}</div>
          <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 14 }}>{t('total_all_cats')}</div>
          <div className="serif" style={{ fontSize: 42, fontWeight: 500, color: 'var(--ink-900)', letterSpacing: -1, fontVariantNumeric: 'tabular-nums' }}>{fmtMoney(2400, currency)}</div>
          <div style={{ height: 8, background: 'var(--cream-200)', borderRadius: 4, marginTop: 12, overflow: 'hidden' }}>
            <div style={{ width: '62%', height: '100%', background: 'linear-gradient(90deg, var(--cream-400), var(--accent-amber))' }}/>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, color: 'var(--ink-500)', marginTop: 6 }}>
            <span>{fmtMoney(1485, currency)} spent</span>
            <span>{fmtMoney(915, currency)} left · 9 days</span>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
            <APButton variant="outline" size="sm" icon="pencil">{t('edit_cap')}</APButton>
            <APButton variant="ghost" size="sm">{t('use_last_avg')}</APButton>
          </div>
        </PaperCard>

        <PaperCard padding={20}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-900)', marginBottom: 4 }}>{t('savings_target')}</div>
          <div style={{ fontSize: 12, color: 'var(--ink-500)', marginBottom: 14 }}>{t('auto_sweeps')}</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <div className="serif" style={{ fontSize: 42, fontWeight: 500, color: 'var(--pos-500)', letterSpacing: -1 }}>25%</div>
            <div style={{ fontSize: 13, color: 'var(--ink-500)' }}>of monthly income</div>
          </div>
          <div style={{ marginTop: 12, display: 'flex', gap: 5 }}>
            {[10, 15, 20, 25, 30, 40, 50].map(p => (
              <button key={p} style={{
                flex: 1, padding: '6px 0', borderRadius: 7,
                border: p === 25 ? '1px solid var(--ink-900)' : '1px solid var(--ink-200)',
                background: p === 25 ? 'var(--ink-900)' : 'var(--cream-50)',
                color: p === 25 ? 'var(--cream-50)' : 'var(--ink-900)',
                fontSize: 11.5, fontWeight: 600, cursor: 'pointer', fontFamily: 'var(--font-ui)',
              }}>{p}%</button>
            ))}
          </div>
          <div style={{ fontSize: 11.5, color: 'var(--ink-500)', marginTop: 10 }}>
            At 25%, MITA will sweep <strong style={{ color: 'var(--ink-900)' }}>{fmtMoney(525, currency)}</strong> on your next payday.
          </div>
        </PaperCard>
      </div>

      <PaperCard padding={0} style={{ marginBottom: 16 }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-900)' }}>{t('per_category_caps')}</div>
            <div style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>{t('nudges_at_80')}</div>
          </div>
          <div style={{ flex: 1 }} />
          <APButton variant="outline" size="sm" icon="plus">{t('add_cap')}</APButton>
        </div>
        {SAMPLE.categoryBreakdown.map((c, i) => {
          const cap = Math.round(c.amt * 1.2);
          const pct = (c.amt / cap) * 100;
          return (
            <div key={c.cat} style={{ padding: '12px 20px', display: 'grid', gridTemplateColumns: '130px 1fr 140px', gap: 14, alignItems: 'center', borderBottom: i < SAMPLE.categoryBreakdown.length - 1 ? '1px solid var(--ink-100)' : 'none' }}>
              <CatPill cat={c.cat} />
              <div>
                <div style={{ height: 6, background: 'var(--cream-200)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ width: `${pct}%`, height: '100%', background: CAT_COLORS[c.cat].dot }}/>
                </div>
                <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 4 }}>
                  {fmtMoney(c.amt, currency)} of {fmtMoney(cap, currency)} · {Math.round(pct)}%
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
                <button style={{ border: '1px solid var(--ink-200)', background: 'var(--cream-50)', borderRadius: 7, padding: '4px 10px', fontSize: 11.5, cursor: 'pointer', fontFamily: 'var(--font-ui)' }}>{t('edit')}</button>
                <button style={{ border: 'none', background: 'transparent', color: 'var(--ink-400)', cursor: 'pointer', width: 28, height: 28 }}>
                  <Icon name="ellipsis" size={14}/>
                </button>
              </div>
            </div>
          );
        })}
      </PaperCard>

      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-900)', marginBottom: 10 }}>{t('savings_goals')}</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <GoalCard emoji="✈" title="Kyoto trip" current={1240} target={2400} currency={currency} due="Jun 15" />
        <GoalCard emoji="💻" title="New laptop" current={820}  target={1800} currency={currency} due="Aug 1"  />
        <GoalCard emoji="🏔" title="Emergency fund" current={4200} target={6000} currency={currency} due="Dec 31" />
      </div>
    </div>
  );
}

function CategoriesScreen() {
  const { t, lang } = useT();
  return (
    <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '20px 24px 100px' }}>
      <div style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.2, color: 'var(--ink-500)' }}>{t('categories_eyebrow')}</div>
        <h1 className="serif" style={{ fontSize: 28, fontWeight: 500, color: 'var(--ink-900)', letterSpacing: -0.5 }}>{t('categories_title')}</h1>
      </div>

      <PaperCard padding={0}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center' }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-900)' }}>9 categories · 2 custom rules</div>
          <div style={{ flex: 1 }} />
          <APButton variant="outline" size="sm" icon="plus">{t('new_category')}</APButton>
        </div>
        {Object.entries(CAT_COLORS).map(([cat, col], i, arr) => (
          <div key={cat} style={{ padding: '12px 20px', display: 'grid', gridTemplateColumns: '40px 1fr 150px 120px 36px', gap: 12, alignItems: 'center', borderBottom: i < arr.length - 1 ? '1px solid var(--ink-100)' : 'none' }}>
            <div style={{ width: 30, height: 30, borderRadius: 9, background: col.bg, border: `1px solid ${col.dot}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: col.dot }}>
              <span style={{ width: 9, height: 9, borderRadius: 5, background: col.dot }}/>
            </div>
            <div>
              <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-900)' }}>{cat}</div>
              <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>Keywords: coffee, restaurant, grocer, ramen…</div>
            </div>
            <div style={{ fontSize: 12, color: 'var(--ink-500)', fontVariantNumeric: 'tabular-nums' }}>
              <strong style={{ color: 'var(--ink-900)' }}>{[24,1,8,12,6,4,2,1,3][i]}</strong> rules
            </div>
            <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>Auto-assign <span style={{ color: 'var(--pos-500)', fontWeight: 600 }}>on</span></div>
            <button style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--ink-400)' }}><Icon name="ellipsis" size={14}/></button>
          </div>
        ))}
      </PaperCard>
    </div>
  );
}

Object.assign(window, { RecordsScreen, ImportScreen, BudgetScreen, CategoriesScreen, SettingsScreen, ManualField });

// ───────────────────────────────────────────────────────────────
// SettingsScreen — profile, appearance, import pipeline, API keys
// ───────────────────────────────────────────────────────────────

// Small UI helpers local to settings
function SettingsSection({ id, eyebrow, title, sub, children }) {
  return (
    <section id={id} style={{ marginBottom: 36, scrollMarginTop: 20 }}>
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 10.5, textTransform: 'uppercase', letterSpacing: 1.3, color: 'var(--ink-500)', fontWeight: 600 }}>{eyebrow}</div>
        <div className="serif" style={{ fontSize: 22, fontWeight: 500, color: 'var(--ink-900)', letterSpacing: -0.3, marginTop: 2 }}>{title}</div>
        {sub && <div style={{ fontSize: 12.5, color: 'var(--ink-500)', marginTop: 4, maxWidth: 640 }}>{sub}</div>}
      </div>
      {children}
    </section>
  );
}

function SettingRow({ label, hint, children, align = 'center' }) {
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '240px 1fr', gap: 20,
      padding: '14px 20px', borderBottom: '1px solid var(--ink-100)', alignItems: align,
    }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>{label}</div>
        {hint && <div style={{ fontSize: 11.5, color: 'var(--ink-500)', marginTop: 3, lineHeight: 1.45 }}>{hint}</div>}
      </div>
      <div>{children}</div>
    </div>
  );
}

function PillChoice({ value, onChange, options }) {
  return (
    <div style={{ display: 'inline-flex', gap: 6, flexWrap: 'wrap' }}>
      {options.map(o => {
        const on = value === o.id;
        return (
          <button key={o.id} onClick={() => onChange(o.id)} style={{
            padding: '7px 12px', borderRadius: 8,
            border: on ? '1.5px solid var(--ink-900)' : '1px solid var(--ink-200)',
            background: on ? 'var(--ink-900)' : 'var(--cream-50)',
            color: on ? 'var(--cream-50)' : 'var(--ink-900)',
            fontSize: 12.5, fontWeight: on ? 600 : 500, cursor: 'pointer',
            fontFamily: 'var(--font-ui)', display: 'inline-flex', alignItems: 'center', gap: 6,
          }}>
            {o.icon && <Icon name={o.icon} size={13}/>}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function Select({ value, onChange, options, width = 260 }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)} style={{
      height: 34, width, padding: '0 10px', borderRadius: 9,
      border: '1px solid var(--ink-200)', background: 'var(--cream-50)',
      color: 'var(--ink-900)', fontSize: 13, fontFamily: 'var(--font-ui)', cursor: 'pointer',
    }}>
      {options.map(o => <option key={o.id || o.value || o} value={o.id || o.value || o}>{o.label || o}</option>)}
    </select>
  );
}

function Input({ value, onChange, placeholder, type = 'text', width = '100%', mono = false }) {
  return (
    <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={{
      height: 34, width, padding: '0 11px', borderRadius: 9,
      border: '1px solid var(--ink-200)', background: 'var(--cream-50)',
      color: 'var(--ink-900)', fontSize: 13,
      fontFamily: mono ? 'ui-monospace, SFMono-Regular, Menlo, monospace' : 'var(--font-ui)',
      outline: 'none',
    }} />
  );
}

function Switch({ checked, onChange }) {
  return (
    <button onClick={() => onChange(!checked)} style={{
      width: 40, height: 22, borderRadius: 12,
      border: 'none', cursor: 'pointer', position: 'relative',
      background: checked ? 'var(--pos-500)' : 'var(--ink-200)',
      transition: 'background 160ms',
    }}>
      <span style={{
        position: 'absolute', top: 2, left: checked ? 20 : 2,
        width: 18, height: 18, borderRadius: 9, background: '#fff',
        boxShadow: '0 1px 3px rgba(0,0,0,.2)', transition: 'left 160ms',
      }}/>
    </button>
  );
}

const LLM_MODELS = [
  { id: 'gpt-4o',                label: 'GPT-4o · OpenAI',              tier: 'fast',    vision: true  },
  { id: 'gpt-4o-mini',           label: 'GPT-4o mini · OpenAI',         tier: 'cheap',   vision: true  },
  { id: 'claude-sonnet-4-5',     label: 'Claude Sonnet 4.5 · Anthropic', tier: 'smart',  vision: true  },
  { id: 'claude-haiku-4-5',      label: 'Claude Haiku 4.5 · Anthropic', tier: 'fast',    vision: true  },
  { id: 'gemini-2.5-pro',        label: 'Gemini 2.5 Pro · Google',      tier: 'smart',   vision: true  },
  { id: 'gemini-2.5-flash',      label: 'Gemini 2.5 Flash · Google',    tier: 'fast',    vision: true  },
  { id: 'deepseek-v3',           label: 'DeepSeek v3 · DeepSeek',       tier: 'cheap',   vision: false },
  { id: 'qwen-2.5-vl-72b',       label: 'Qwen 2.5 VL 72B · Alibaba',    tier: 'cheap',   vision: true  },
  { id: 'local-llama-3.1-8b',    label: 'Llama 3.1 8B · local (Ollama)', tier: 'local',  vision: false },
];
const OCR_ENGINES = [
  { id: 'tesseract', label: 'Tesseract (on-device)', sub: 'Fast · free · weaker on handwriting' },
  { id: 'paddleocr', label: 'PaddleOCR (on-device)', sub: 'Better for CJK · heavier' },
  { id: 'textract',  label: 'AWS Textract',          sub: 'Cloud · $1.50 / 1k pages' },
  { id: 'google-vision', label: 'Google Vision',     sub: 'Cloud · best layout · $1.50 / 1k' },
];
const PROVIDERS = [
  { id: 'openai',    label: 'OpenAI',        env: 'OPENAI_API_KEY',    placeholder: 'sk-...' },
  { id: 'anthropic', label: 'Anthropic',     env: 'ANTHROPIC_API_KEY', placeholder: 'sk-ant-...' },
  { id: 'google',    label: 'Google (Gemini)', env: 'GOOGLE_API_KEY',  placeholder: 'AIza...' },
  { id: 'deepseek',  label: 'DeepSeek',      env: 'DEEPSEEK_API_KEY',  placeholder: 'sk-...' },
  { id: 'alibaba',   label: 'Alibaba (Qwen)', env: 'DASHSCOPE_API_KEY', placeholder: 'sk-...' },
  { id: 'textract',  label: 'AWS Textract',  env: 'AWS_ACCESS_KEY_ID', placeholder: 'AKIA...', extra: 'AWS_SECRET_ACCESS_KEY' },
  { id: 'gvision',   label: 'Google Vision', env: 'GOOGLE_VISION_KEY', placeholder: 'AIza...' },
  { id: 'ollama',    label: 'Ollama (local)', env: 'OLLAMA_HOST',      placeholder: 'http://localhost:11434' },
];

// Pipeline stage — OCR / Structuring / Classification
function PipelineStage({ title, desc, icon, options, value, onChange, model, onModel, showModel }) {
  const { t } = useT();
  return (
    <div style={{
      padding: 18, borderRadius: 12,
      background: 'var(--cream-50)', border: '1px solid var(--ink-200)',
      display: 'flex', flexDirection: 'column', gap: 14,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          width: 34, height: 34, borderRadius: 9,
          background: 'var(--cream-200)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--ink-700)',
        }}><Icon name={icon} size={17}/></div>
        <div>
          <div className="hand" style={{ fontSize: 17, fontWeight: 600, color: 'var(--ink-900)' }}>{title}</div>
          <div style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>{desc}</div>
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {options.map(o => {
          const on = value === o.id;
          return (
            <button key={o.id} onClick={() => onChange(o.id)} style={{
              textAlign: 'left', padding: '10px 12px', borderRadius: 9, cursor: 'pointer',
              border: on ? '1.5px solid var(--ink-900)' : '1px solid var(--ink-200)',
              background: on ? 'var(--cream-200)' : 'var(--cream-50)',
              color: 'var(--ink-900)', fontFamily: 'var(--font-ui)',
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <span style={{
                width: 14, height: 14, borderRadius: 7, flexShrink: 0,
                border: on ? '4px solid var(--ink-900)' : '1.5px solid var(--ink-300)',
                background: on ? 'var(--cream-50)' : 'transparent',
              }}/>
              <span style={{ flex: 1 }}>
                <div style={{ fontSize: 12.5, fontWeight: on ? 700 : 500 }}>{o.label}</div>
                {o.sub && <div style={{ fontSize: 10.5, color: 'var(--ink-500)', marginTop: 2 }}>{o.sub}</div>}
              </span>
              {o.badge && <span style={{ fontSize: 10, padding: '2px 7px', borderRadius: 5, background: o.badgeBg || 'var(--cream-300)', color: 'var(--ink-700)', fontWeight: 600 }}>{o.badge}</span>}
            </button>
          );
        })}
      </div>
      {showModel && (
        <div style={{ paddingTop: 8, borderTop: '1px dashed var(--ink-200)' }}>
          <div style={{ fontSize: 10.5, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--ink-500)', fontWeight: 600, marginBottom: 6 }}>{t('llm_model')}</div>
          <Select value={model} onChange={onModel} options={LLM_MODELS.map(m => ({ id: m.id, label: m.label }))} width="100%"/>
        </div>
      )}
    </div>
  );
}

function ApiKeyRow({ provider, value, onChange, revealed, onReveal, extra, onExtra }) {
  const { t } = useT();
  const [hover, setHover] = React.useState(false);
  return (
    <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--ink-100)' }}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
      <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr 100px', gap: 14, alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>{provider.label}</div>
          <div style={{ fontSize: 10.5, color: 'var(--ink-500)', fontFamily: 'ui-monospace, Menlo, monospace', marginTop: 2 }}>{provider.env}</div>
        </div>
        <Input
          value={value}
          onChange={onChange}
          placeholder={provider.placeholder}
          type={revealed ? 'text' : 'password'}
          mono
        />
        <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end', alignItems: 'center' }}>
          <button onClick={onReveal} title={revealed ? 'Hide' : 'Show'} style={{
            width: 30, height: 30, borderRadius: 7, border: '1px solid var(--ink-200)',
            background: 'var(--cream-50)', cursor: 'pointer', color: 'var(--ink-500)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><Icon name={revealed ? 'chevron-down' : 'search'} size={13}/></button>
          {value ? (
            <span style={{ fontSize: 10.5, padding: '3px 8px', borderRadius: 5, background: '#E6F2EA', color: 'var(--pos-500)', fontWeight: 700 }}>{t('set')}</span>
          ) : (
            <span style={{ fontSize: 10.5, padding: '3px 8px', borderRadius: 5, background: 'var(--cream-200)', color: 'var(--ink-500)', fontWeight: 600 }}>—</span>
          )}
        </div>
      </div>
      {provider.extra && (
        <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr 100px', gap: 14, alignItems: 'center', marginTop: 8 }}>
          <div style={{ fontSize: 11, color: 'var(--ink-500)', fontFamily: 'ui-monospace, Menlo, monospace', paddingLeft: 4 }}>{provider.extra}</div>
          <Input value={extra} onChange={onExtra} placeholder="AWS secret key" type={revealed ? 'text' : 'password'} mono/>
          <div/>
        </div>
      )}
    </div>
  );
}

function SettingsScreen({ currency, theme, setTheme, lang, setLang, preferredName = '', setPreferredName, accountName = 'Lena Chen', setAccountName }) {
  const { t } = useT();
  // local-state config (prototype only)
  const [profile, setProfile] = React.useState({
    email: 'lena@mita.finance', timezone: 'America/Los_Angeles',
  });
  const setFullName = (v) => setAccountName && setAccountName(v);
  const [ocrEngine, setOcrEngine] = React.useState('paddleocr');
  const [ocrMode, setOcrMode] = React.useState('ocr'); // 'ocr' | 'llm'
  const [ocrLlm, setOcrLlm] = React.useState('gpt-4o');
  const [structMode, setStructMode] = React.useState('hybrid'); // regex | llm | hybrid
  const [structLlm, setStructLlm] = React.useState('claude-haiku-4-5');
  const [classMode, setClassMode] = React.useState('hybrid');
  const [classLlm, setClassLlm] = React.useState('gpt-4o-mini');

  const [keys, setKeys] = React.useState({
    openai: 'sk-proj-••••••••••••••••••••••',
    anthropic: '',
    google: 'AIzaSy••••••••••••••••••',
    deepseek: '',
    alibaba: '',
    textract: '',
    textract_secret: '',
    gvision: '',
    ollama: 'http://localhost:11434',
  });
  const [revealed, setRevealed] = React.useState({});

  const [notif, setNotif] = React.useState({
    weekly: true, threshold80: true, largeTxn: true, duplicates: false,
    quietStart: '22:00', quietEnd: '08:00',
  });
  const [privacy, setPrivacy] = React.useState({
    onDevice: true, cloudBackup: false, telemetry: false,
  });
  const [appearance, setAppearance] = React.useState({
    density: 'comfortable', handMode: 'hand',
  });

  const sections = [
    { id: 'profile',    label: t('sec_profile'),    icon: 'user' },
    { id: 'appearance', label: t('sec_appearance'), icon: 'sun' },
    { id: 'pipeline',   label: t('sec_pipeline'),   icon: 'sparkles' },
    { id: 'keys',       label: t('sec_keys'),       icon: 'settings' },
    { id: 'notifs',     label: t('sec_notifs'),     icon: 'mail' },
    { id: 'privacy',    label: t('sec_privacy'),    icon: 'eye' },
    { id: 'about',      label: t('sec_about'),      icon: 'file-text' },
  ];
  const [activeAnchor, setActiveAnchor] = React.useState('profile');

  return (
    <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '20px 24px 100px', position: 'relative' }}>
      <div style={{ marginBottom: 22, maxWidth: 1060, margin: '0 auto 22px' }}>
        <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.2, color: 'var(--ink-500)' }}>{t('settings_eyebrow')}</div>
        <h1 className="serif" style={{ fontSize: 28, fontWeight: 500, color: 'var(--ink-900)', letterSpacing: -0.5 }}>{t('settings_title')}</h1>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 28, maxWidth: 1060, margin: '0 auto' }}>
        {/* Sticky left nav */}
        <aside style={{ position: 'sticky', top: 0, alignSelf: 'start', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {sections.map(s => {
            const on = activeAnchor === s.id;
            return (
              <a key={s.id} href={`#${s.id}`} onClick={(e) => {
                e.preventDefault();
                setActiveAnchor(s.id);
                const el = document.getElementById(s.id);
                if (el) el.parentElement.parentElement.parentElement.scrollTo({ top: el.offsetTop - 20, behavior: 'smooth' });
              }} style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '8px 11px',
                borderRadius: 8, textDecoration: 'none',
                background: on ? 'var(--cream-200)' : 'transparent',
                color: on ? 'var(--ink-900)' : 'var(--ink-700)',
                fontSize: 13, fontWeight: on ? 600 : 500, fontFamily: 'var(--font-ui)',
              }}>
                <Icon name={s.icon} size={15}/>
                <span>{s.label}</span>
              </a>
            );
          })}
        </aside>

        {/* Settings content */}
        <div>
          {/* PROFILE */}
          <SettingsSection id="profile" eyebrow={t('profile_eyebrow')} title={t('profile_title')} sub={t('profile_sub')}>
            <PaperCard padding={0}>
              <div style={{ padding: '18px 20px', display: 'flex', alignItems: 'center', gap: 14, borderBottom: '1px solid var(--ink-100)' }}>
                <div style={{
                  width: 48, height: 48, borderRadius: 24,
                  background: 'linear-gradient(135deg, var(--cream-400), var(--accent-amber))',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: 'var(--font-hand)', fontSize: 22, fontWeight: 700, color: 'var(--ink-900)',
                }}>L</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-900)' }}>{profile.name}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>{profile.email} · {t('free_plan')}</div>
                </div>
                <APButton variant="outline" size="sm">{t('change_photo')}</APButton>
                <APButton variant="ghost" size="sm">{t('upgrade')}</APButton>
              </div>
              <SettingRow label={t('full_name')}>
                <Input value={profile.name} onChange={v => setProfile({ ...profile, name: v })} width={320}/>
              </SettingRow>
              <SettingRow label={t('preferred_name')} hint={t('preferred_name_hint', { first: (accountName || '').split(' ')[0] })}>
                <Input
                  value={preferredName}
                  onChange={v => setPreferredName && setPreferredName(v)}
                  placeholder={(profile.name || '').split(' ')[0] || 'e.g. Rei'}
                  width={320}
                />
              </SettingRow>
              <SettingRow label={t('email')}>
                <Input value={profile.email} onChange={v => setProfile({ ...profile, email: v })} width={320}/>
              </SettingRow>
              <SettingRow label={t('time_zone')} hint={t('time_zone_hint')}>
                <Select value={profile.timezone} onChange={v => setProfile({ ...profile, timezone: v })} options={[
                  { id: 'America/Los_Angeles', label: 'America/Los_Angeles · PDT' },
                  { id: 'America/New_York', label: 'America/New_York · EDT' },
                  { id: 'Asia/Tokyo', label: 'Asia/Tokyo · JST' },
                  { id: 'Asia/Shanghai', label: 'Asia/Shanghai · CST' },
                  { id: 'Europe/London', label: 'Europe/London · BST' },
                ]} width={320}/>
              </SettingRow>
              <SettingRow label={t('default_currency')} hint={t('default_currency_hint')}>
                <PillChoice value={currency} onChange={() => {}} options={[
                  { id: 'USD', label: 'USD $' }, { id: 'JPY', label: 'JPY ¥' }, { id: 'CNY', label: 'CNY ¥' }, { id: 'EUR', label: 'EUR €' },
                ]}/>
              </SettingRow>
            </PaperCard>
          </SettingsSection>

          {/* APPEARANCE */}
          <SettingsSection id="appearance" eyebrow={t('appearance_eyebrow')} title={t('appearance_title')} sub={t('appearance_sub')}>
            <PaperCard padding={0}>
              <SettingRow label={t('theme')}>
                <PillChoice value={theme} onChange={setTheme} options={[
                  { id: 'light', label: t('light'), icon: 'sun' },
                  { id: 'dark',  label: t('dark'),  icon: 'moon' },
                ]}/>
              </SettingRow>
              <SettingRow label={t('settings_language')} hint={t('settings_language_hint')}>
                <PillChoice value={lang} onChange={setLang} options={[
                  { id: 'en', label: 'English' }, { id: 'ja', label: '日本語' }, { id: 'zh', label: '简体中文' },
                ]}/>
              </SettingRow>
            </PaperCard>
          </SettingsSection>

          {/* IMPORT PIPELINE */}
          <SettingsSection id="pipeline" eyebrow={t('pipeline_eyebrow')} title={t('pipeline_title')} sub={t('pipeline_sub')}>
            {/* Flow diagram */}
            <div style={{
              display: 'flex', alignItems: 'stretch', gap: 8, padding: 14,
              background: 'var(--cream-100)', border: '1px dashed var(--ink-300)', borderRadius: 12,
              marginBottom: 14,
            }}>
              {[
                { label: t('stage_raw'), sub: t('stage_raw_sub') },
                { label: t('stage_ocr'), sub: ocrMode === 'llm' ? `LLM · ${ocrLlm}` : OCR_ENGINES.find(e => e.id === ocrEngine)?.label },
                { label: t('stage_structure'), sub: structMode === 'regex' ? 'regex only' : structMode === 'llm' ? `LLM · ${structLlm}` : `regex + LLM · ${structLlm}` },
                { label: t('stage_classify'), sub: classMode === 'regex' ? 'regex only' : classMode === 'llm' ? `LLM · ${classLlm}` : `regex + LLM · ${classLlm}` },
                { label: t('stage_record'), sub: t('stage_record_sub') },
              ].map((step, i, arr) => (
                <React.Fragment key={i}>
                  <div style={{ flex: 1, padding: 10, background: 'var(--cream-50)', borderRadius: 9, border: '1px solid var(--ink-200)' }}>
                    <div style={{ fontSize: 10.5, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--ink-500)', fontWeight: 700 }}>{i+1}</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)', marginTop: 2 }}>{step.label}</div>
                    <div style={{ fontSize: 10.5, color: 'var(--ink-500)', marginTop: 2, lineHeight: 1.4 }}>{step.sub}</div>
                  </div>
                  {i < arr.length - 1 && (
                    <div style={{ display: 'flex', alignItems: 'center', color: 'var(--ink-400)' }}>
                      <Icon name="arrow-right" size={14}/>
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
              <PipelineStage
                title={t('stage_ocr')} icon="eye"
                desc={t('ocr_desc')}
                value={ocrMode} onChange={setOcrMode}
                showModel={ocrMode === 'llm'} model={ocrLlm} onModel={setOcrLlm}
                options={[
                  { id: 'ocr',  label: t('ocr_option'), sub: OCR_ENGINES.find(e => e.id === ocrEngine)?.label, badge: t('fast') },
                  { id: 'llm',  label: t('vision_llm'), sub: t('vision_llm_sub'), badge: t('smart') },
                ]}
              />
              <PipelineStage
                title={t('stage_structure')} icon="list-todo"
                desc={t('struct_desc')}
                value={structMode} onChange={setStructMode}
                showModel={structMode !== 'regex'} model={structLlm} onModel={setStructLlm}
                options={[
                  { id: 'regex',  label: t('regex'), sub: t('regex_sub'), badge: t('cheap') },
                  { id: 'llm',    label: t('llm'), sub: t('llm_sub') },
                  { id: 'hybrid', label: t('regex_plus_llm'), sub: t('regex_plus_llm_sub'), badge: t('recommended'), badgeBg: '#E6F2EA' },
                ]}
              />
              <PipelineStage
                title={t('stage_classify')} icon="folder"
                desc={t('classify_desc')}
                value={classMode} onChange={setClassMode}
                showModel={classMode !== 'regex'} model={classLlm} onModel={setClassLlm}
                options={[
                  { id: 'regex',  label: t('keyword_rules'), sub: t('keyword_rules_sub'), badge: t('cheap') },
                  { id: 'llm',    label: t('llm_context'), sub: t('llm_context_sub') },
                  { id: 'hybrid', label: t('rules_plus_llm'), sub: t('rules_plus_llm_sub'), badge: t('recommended'), badgeBg: '#E6F2EA' },
                ]}
              />
            </div>

            {/* OCR engine sub-picker when "OCR engine" mode is selected */}
            {ocrMode === 'ocr' && (
              <PaperCard padding={0} style={{ marginTop: 14 }}>
                <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)' }}>{t('ocr_engine_label')}</div>
                    <div style={{ fontSize: 11.5, color: 'var(--ink-500)' }}>{t('ocr_engine_hint')}</div>
                  </div>
                </div>
                {OCR_ENGINES.map((e, i) => {
                  const on = ocrEngine === e.id;
                  return (
                    <button key={e.id} onClick={() => setOcrEngine(e.id)} style={{
                      display: 'flex', alignItems: 'center', gap: 12, padding: '12px 20px',
                      borderBottom: i < OCR_ENGINES.length - 1 ? '1px solid var(--ink-100)' : 'none',
                      background: on ? 'var(--cream-100)' : 'transparent',
                      border: 'none', borderLeft: on ? '3px solid var(--ink-900)' : '3px solid transparent',
                      cursor: 'pointer', width: '100%', textAlign: 'left',
                      fontFamily: 'var(--font-ui)',
                    }}>
                      <span style={{ width: 14, height: 14, borderRadius: 7,
                        border: on ? '4px solid var(--ink-900)' : '1.5px solid var(--ink-300)',
                        background: on ? 'var(--cream-50)' : 'transparent',
                      }}/>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 13, fontWeight: on ? 700 : 500, color: 'var(--ink-900)' }}>{e.label}</div>
                        <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 2 }}>{e.sub}</div>
                      </div>
                    </button>
                  );
                })}
              </PaperCard>
            )}
          </SettingsSection>

          {/* API KEYS */}
          <SettingsSection id="keys" eyebrow={t('keys_eyebrow')} title={t('keys_title')}
            sub={t('keys_sub')}>
            <PaperCard padding={0}>
              <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--ink-200)', display: 'flex', alignItems: 'center', gap: 10 }}>
                <Icon name="sparkles" size={15}/>
                <div style={{ fontSize: 12.5, color: 'var(--ink-700)' }}>{t('keys_note')}</div>
                <div style={{ flex: 1 }}/>
                <APButton variant="ghost" size="sm" icon="download">{t('export_env')}</APButton>
                <APButton variant="outline" size="sm" icon="upload">{t('import_env')}</APButton>
              </div>
              {PROVIDERS.map((p, i) => (
                <ApiKeyRow key={p.id} provider={p}
                  value={keys[p.id] || ''}
                  onChange={v => setKeys({ ...keys, [p.id]: v })}
                  extra={keys[`${p.id}_secret`] || ''}
                  onExtra={v => setKeys({ ...keys, [`${p.id}_secret`]: v })}
                  revealed={!!revealed[p.id]}
                  onReveal={() => setRevealed({ ...revealed, [p.id]: !revealed[p.id] })}
                />
              ))}
              <div style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', gap: 10 }}>
                <Icon name="file-text" size={14}/>
                <div style={{ fontSize: 11.5, color: 'var(--ink-500)', flex: 1 }}>
                  {t('env_help')} <code style={{ fontFamily: 'ui-monospace, Menlo, monospace', background: 'var(--cream-200)', padding: '1px 5px', borderRadius: 4 }}>~/.mita/.env</code>{t('env_help_2')}
                </div>
              </div>
            </PaperCard>

            {/* .env preview */}
            <div style={{
              marginTop: 12, padding: 16, borderRadius: 12,
              background: '#1F1D19', color: '#E8DFD0',
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
              fontSize: 11.5, lineHeight: 1.75, position: 'relative',
            }}>
              <div style={{ position: 'absolute', top: 10, right: 12, fontSize: 10, color: '#8A7F6F', letterSpacing: 1, textTransform: 'uppercase' }}>{t('env_preview')}</div>
              <div style={{ color: '#8A7F6F' }}># MITA — provider credentials</div>
              {PROVIDERS.map(p => {
                const v = keys[p.id];
                const masked = v ? (revealed[p.id] ? v : v.slice(0, 6) + '•'.repeat(Math.max(0, v.length - 6))) : '';
                return (
                  <div key={p.id}>
                    <span style={{ color: '#D9A86C' }}>{p.env}</span>
                    <span>=</span>
                    <span style={{ color: v ? '#B8D4A8' : '#6B6357' }}>{v ? `"${masked}"` : '""'}</span>
                  </div>
                );
              })}
            </div>
          </SettingsSection>

          {/* NOTIFICATIONS */}
          <SettingsSection id="notifs" eyebrow="Notifications" title="When MITA speaks up">
            <PaperCard padding={0}>
              <SettingRow label="Weekly digest" hint="Sunday 9am · your week in cash flow.">
                <Switch checked={notif.weekly} onChange={v => setNotif({ ...notif, weekly: v })}/>
              </SettingRow>
              <SettingRow label="Budget alerts" hint="Nudge when any category passes 80% of its cap.">
                <Switch checked={notif.threshold80} onChange={v => setNotif({ ...notif, threshold80: v })}/>
              </SettingRow>
              <SettingRow label="Large transactions" hint="Flag anything above $200.">
                <Switch checked={notif.largeTxn} onChange={v => setNotif({ ...notif, largeTxn: v })}/>
              </SettingRow>
              <SettingRow label="Duplicate detection" hint="Ask before saving a possible duplicate.">
                <Switch checked={notif.duplicates} onChange={v => setNotif({ ...notif, duplicates: v })}/>
              </SettingRow>
              <SettingRow label="Quiet hours" hint="MITA won't notify during this window.">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Input value={notif.quietStart} onChange={v => setNotif({ ...notif, quietStart: v })} width={90}/>
                  <span style={{ color: 'var(--ink-500)' }}>→</span>
                  <Input value={notif.quietEnd} onChange={v => setNotif({ ...notif, quietEnd: v })} width={90}/>
                </div>
              </SettingRow>
            </PaperCard>
          </SettingsSection>

          {/* PRIVACY */}
          <SettingsSection id="privacy" eyebrow="Data & privacy" title="Where your data lives">
            <PaperCard padding={0}>
              <SettingRow label="On-device processing" hint="Run OCR and parsing locally. LLM calls still go to their provider.">
                <Switch checked={privacy.onDevice} onChange={v => setPrivacy({ ...privacy, onDevice: v })}/>
              </SettingRow>
              <SettingRow label="Encrypted cloud backup" hint="End-to-end encrypted · your key, not ours.">
                <Switch checked={privacy.cloudBackup} onChange={v => setPrivacy({ ...privacy, cloudBackup: v })}/>
              </SettingRow>
              <SettingRow label="Anonymous telemetry" hint="Help improve MITA. No transaction data leaves the device.">
                <Switch checked={privacy.telemetry} onChange={v => setPrivacy({ ...privacy, telemetry: v })}/>
              </SettingRow>
              <SettingRow label="Your data" hint="Export everything as JSON, or wipe the local database.">
                <div style={{ display: 'flex', gap: 8 }}>
                  <APButton variant="outline" size="sm" icon="download">Export all data</APButton>
                  <APButton variant="ghost" size="sm" style={{ color: 'var(--neg-500)' }}>Delete everything…</APButton>
                </div>
              </SettingRow>
            </PaperCard>
          </SettingsSection>

          {/* ABOUT */}
          <SettingsSection id="about" eyebrow="About" title="MITA v0.4.2">
            <PaperCard padding={20} style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <div style={{
                width: 48, height: 48, borderRadius: 12,
                background: 'linear-gradient(135deg, var(--cream-400), var(--accent-amber))',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'var(--font-hand)', fontSize: 26, fontWeight: 700, color: 'var(--ink-900)',
              }}>¥</div>
              <div style={{ flex: 1 }}>
                <div className="brand-hand" style={{ fontSize: 20, color: 'var(--ink-900)' }}>MITA Finance</div>
                <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>Build 0.4.2 (2026-04-12) · on-device finance agent</div>
              </div>
              <APButton variant="ghost" size="sm">Release notes</APButton>
              <APButton variant="ghost" size="sm">Licenses</APButton>
              <APButton variant="outline" size="sm">Check for updates</APButton>
            </PaperCard>
          </SettingsSection>
        </div>
      </div>
    </div>
  );
}
