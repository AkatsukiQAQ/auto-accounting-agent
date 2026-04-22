// Shared chrome: left sidebar, top bar, FAB chatbot overlay.

function LeftSidebar({ active, onNav, collapsed, onToggle, variant = 'A' }) {
  const { t } = useT();
  const items = [
    { id: 'dashboard', icon: 'layout-grid', label: t('nav_dashboard') },
    { id: 'records',   icon: 'list',        label: t('nav_records') },
    { id: 'import',    icon: 'upload',      label: t('nav_import') },
    { id: 'review',    icon: 'sparkles',    label: t('nav_review') },
    { id: 'accounts',  icon: 'folder',      label: t('nav_accounts') },
    { id: 'recurring', icon: 'clock',       label: t('nav_recurring') },
    { id: 'budget',    icon: 'list-todo',   label: t('nav_budget') },
    { id: 'categories',icon: 'folder',      label: t('nav_categories') },
    { id: 'settings',  icon: 'settings',    label: t('nav_settings') },
  ];
  const width = collapsed ? 68 : 224;

  return (
    <aside style={{
      width, flexShrink: 0, borderRight: '1px solid var(--ink-200)',
      background: 'var(--cream-100)',
      display: 'flex', flexDirection: 'column', padding: '16px 10px',
      transition: 'width 220ms var(--ease)', gap: 4,
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 8px 18px' }}>
        <div style={{
          width: 32, height: 32, borderRadius: 9,
          background: 'linear-gradient(135deg, var(--cream-400), var(--accent-amber))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--font-hand)', fontSize: 22, fontWeight: 700,
          color: 'var(--ink-900)', boxShadow: '0 2px 6px rgba(217,119,6,.25)',
        }}>¥</div>
        {!collapsed && (
          <div style={{ lineHeight: 1.1 }}>
            <div className="brand-hand" style={{ fontSize: 20, color: 'var(--ink-900)', letterSpacing: -0.3 }}>MITA Finance</div>
            <div style={{ fontSize: 10, color: 'var(--ink-500)', letterSpacing: 0.8, textTransform: 'uppercase' }}>{t('brand_tag')}</div>
          </div>
        )}
      </div>

      {/* Nav */}
      {items.map(it => {
        const isActive = active === it.id;
        return (
          <button key={it.id} onClick={() => onNav && onNav(it.id)}
            title={collapsed ? it.label : undefined}
            style={{
              display: 'flex', alignItems: 'center', gap: 11,
              height: 38, padding: collapsed ? 0 : '0 11px',
              justifyContent: collapsed ? 'center' : 'flex-start',
              border: 'none', borderRadius: 10, cursor: 'pointer',
              background: isActive ? 'var(--cream-300)' : 'transparent',
              color: isActive ? 'var(--ink-900)' : 'var(--ink-700)',
              fontFamily: 'var(--font-sans)', fontSize: 13.5, fontWeight: isActive ? 600 : 500,
              transition: 'background 150ms var(--ease)',
            }}
            onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'var(--cream-200)'; }}
            onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}>
            <Icon name={it.icon} size={17} />
            {!collapsed && <span>{it.label}</span>}
          </button>
        );
      })}

      <div style={{ flex: 1 }} />

      {/* Collapse toggle */}
      <button onClick={onToggle}
        style={{
          display: 'flex', alignItems: 'center', gap: 11, height: 34,
          padding: collapsed ? 0 : '0 11px', justifyContent: collapsed ? 'center' : 'flex-start',
          border: '1px solid var(--ink-200)', borderRadius: 9, cursor: 'pointer',
          background: 'var(--cream-50)', color: 'var(--ink-500)',
          fontSize: 12, fontFamily: 'var(--font-sans)',
        }}>
        <Icon name={collapsed ? 'chevron-right' : 'chevron-left'} size={14} />
        {!collapsed && <span>Collapse</span>}
      </button>
    </aside>
  );
}

function TopBar({ currency, onCurrency, theme, onTheme, lang, onLang, user = 'RS', variant = 'A' }) {
  const { t } = useT();
  return (
    <header style={{
      height: 60, flexShrink: 0,
      borderBottom: '1px solid var(--ink-200)',
      background: 'var(--cream-100)',
      display: 'flex', alignItems: 'center', padding: '0 20px', gap: 12,
    }}>
      {/* Search */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        height: 36, padding: '0 12px', borderRadius: 10,
        background: 'var(--cream-50)', border: '1px solid var(--ink-200)',
        width: variant === 'C' ? 360 : 280, color: 'var(--ink-400)', fontSize: 13,
      }}>
        <Icon name="search" size={15} />
        <span style={{ fontFamily: 'var(--font-sans)' }}>{t('search_placeholder')}</span>
        <div style={{ flex: 1 }} />
        <kbd style={{
          fontSize: 10, padding: '2px 6px', borderRadius: 4,
          background: 'var(--cream-200)', color: 'var(--ink-500)',
          border: '1px solid var(--ink-200)', fontFamily: 'var(--font-mono)',
        }}>⌘K</kbd>
      </div>

      <div style={{ flex: 1 }} />

      {/* Right cluster: lang, theme, account */}
      <LanguagePicker value={lang} onChange={onLang} />

      <IconBtn icon={theme === 'dark' ? 'sun' : 'moon'} onClick={() => onTheme(theme === 'dark' ? 'light' : 'dark')} title="Toggle theme" />

      <div style={{ width: 1, height: 24, background: 'var(--ink-200)', margin: '0 4px' }} />

      <AccountMenu user={user} />
    </header>
  );
}

function AccountMenu({ user }) {
  const [open, setOpen] = React.useState(false);
  React.useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [open]);
  const items = [
    { id: 'profile',  label: 'Your account',  icon: null,        sub: 'lena@mita.finance' },
    { id: 'settings', label: 'Settings',      icon: 'settings' },
    { id: 'help',     label: 'Help & shortcuts', icon: 'file-text' },
    { id: 'signout',  label: 'Sign out',      icon: null, danger: true },
  ];
  return (
    <div style={{ position: 'relative' }} onClick={e => e.stopPropagation()}>
      <button onClick={() => setOpen(o => !o)} title="Account" style={{
        width: 34, height: 34, borderRadius: 17, border: 'none', padding: 0,
        background: 'var(--accent-olive)', color: '#fff', cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, fontWeight: 600, fontFamily: 'var(--font-ui)',
        boxShadow: open ? '0 0 0 3px var(--cream-200)' : 'none',
        transition: 'box-shadow 120ms var(--ease)',
      }}>{user}</button>

      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, marginTop: 6,
          background: 'var(--cream-50)', border: '1px solid var(--ink-200)',
          borderRadius: 10, boxShadow: '0 14px 36px rgba(0,0,0,.14)',
          padding: 6, minWidth: 220, zIndex: 30,
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px 10px',
            borderBottom: '1px solid var(--ink-200)', marginBottom: 4,
          }}>
            <div style={{
              width: 34, height: 34, borderRadius: 17, background: 'var(--accent-olive)',
              color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 13, fontWeight: 600, fontFamily: 'var(--font-ui)',
            }}>{user}</div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)', fontFamily: 'var(--font-ui)' }}>Lena Chen</div>
              <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>lena@mita.finance</div>
            </div>
          </div>
          {items.slice(1).map(it => (
            <button key={it.id} onClick={() => setOpen(false)} style={{
              display: 'flex', alignItems: 'center', gap: 10, width: '100%',
              padding: '8px 10px', border: 'none', borderRadius: 7,
              background: 'transparent',
              color: it.danger ? 'var(--neg-500)' : 'var(--ink-900)',
              fontSize: 12.5, fontFamily: 'var(--font-ui)', cursor: 'pointer', textAlign: 'left',
            }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--cream-200)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              {it.icon ? <Icon name={it.icon} size={13} /> : <span style={{ width: 13 }} />}
              <span>{it.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function IconBtn({ icon, onClick, title, active }) {
  return (
    <button onClick={onClick} title={title} style={{
      width: 36, height: 36, borderRadius: 9,
      border: '1px solid transparent', background: active ? 'var(--cream-200)' : 'transparent',
      color: 'var(--ink-700)', cursor: 'pointer',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      transition: 'background 120ms var(--ease)',
    }}
      onMouseEnter={e => e.currentTarget.style.background = 'var(--cream-200)'}
      onMouseLeave={e => e.currentTarget.style.background = active ? 'var(--cream-200)' : 'transparent'}>
      <Icon name={icon} size={16} />
    </button>
  );
}

function SegmentedToggle({ options, value, onChange }) {
  return (
    <div style={{
      display: 'inline-flex', padding: 3, borderRadius: 9,
      background: 'var(--cream-200)', border: '1px solid var(--ink-200)',
    }}>
      {options.map(o => {
        const on = value === o.id;
        return (
          <button key={o.id} onClick={() => onChange(o.id)} style={{
            border: 'none', padding: '4px 10px', borderRadius: 7,
            background: on ? 'var(--cream-50)' : 'transparent',
            color: on ? 'var(--ink-900)' : 'var(--ink-500)',
            fontSize: 12, fontWeight: on ? 600 : 500,
            fontFamily: 'var(--font-ui)', cursor: 'pointer',
            boxShadow: on ? '0 1px 2px rgba(0,0,0,.06)' : 'none',
            transition: 'all 120ms var(--ease)',
          }}>{o.label}</button>
        );
      })}
    </div>
  );
}

function LanguagePicker({ value, onChange }) {
  const [open, setOpen] = React.useState(false);
  const options = [
    { id: 'en', label: 'English',  short: 'EN' },
    { id: 'ja', label: '日本語',    short: 'JA' },
    { id: 'zh', label: '中文',      short: '中' },
  ];
  const cur = options.find(o => o.id === value) || options[0];
  React.useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [open]);
  return (
    <div style={{ position: 'relative' }} onClick={e => e.stopPropagation()}>
      <button onClick={() => setOpen(o => !o)} style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        height: 32, padding: '0 10px', borderRadius: 8,
        border: '1px solid var(--ink-200)', background: 'var(--cream-50)',
        color: 'var(--ink-900)', fontSize: 12, fontWeight: 600,
        fontFamily: 'var(--font-ui)', cursor: 'pointer',
      }}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>
        {cur.short}
        <Icon name="chevron-down" size={12} />
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, marginTop: 4,
          background: 'var(--cream-50)', border: '1px solid var(--ink-200)',
          borderRadius: 9, boxShadow: '0 10px 30px rgba(0,0,0,.12)',
          padding: 4, minWidth: 150, zIndex: 20,
        }}>
          {options.map(o => {
            const on = value === o.id;
            return (
              <button key={o.id} onClick={() => { onChange(o.id); setOpen(false); }} style={{
                display: 'flex', alignItems: 'center', gap: 10, width: '100%',
                padding: '7px 10px', border: 'none', borderRadius: 6,
                background: on ? 'var(--cream-200)' : 'transparent',
                color: 'var(--ink-900)', fontSize: 12.5, fontFamily: 'var(--font-ui)',
                fontWeight: on ? 700 : 400,
                cursor: 'pointer', textAlign: 'left',
              }}>
                <span style={{ color: 'var(--ink-500)', width: 20, fontWeight: on ? 700 : 500 }}>{o.short}</span>
                <span style={{ flex: 1 }}>{o.label}</span>
                {on && <Icon name="check" size={12} />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function CurrencyPicker({ value, onChange }) {
  const [open, setOpen] = React.useState(false);
  const options = ['USD', 'CNY', 'JPY', 'EUR'];
  return (
    <div style={{ position: 'relative' }}>
      <button onClick={() => setOpen(o => !o)} style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        height: 32, padding: '0 10px', borderRadius: 8,
        border: '1px solid var(--ink-200)', background: 'var(--cream-50)',
        color: 'var(--ink-900)', fontSize: 12, fontWeight: 600,
        fontFamily: 'var(--font-ui)', cursor: 'pointer',
      }}>
        <span style={{ color: 'var(--ink-500)' }}>{SYM[value]}</span>
        {value}
        <Icon name="chevron-down" size={12} />
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, marginTop: 4,
          background: 'var(--cream-50)', border: '1px solid var(--ink-200)',
          borderRadius: 9, boxShadow: '0 10px 30px rgba(0,0,0,.12)',
          padding: 4, minWidth: 110, zIndex: 20,
        }}>
          {options.map(o => {
            const on = value === o;
            return (
              <button key={o} onClick={() => { onChange(o); setOpen(false); }} style={{
                display: 'flex', alignItems: 'center', gap: 8, width: '100%',
                padding: '6px 10px', border: 'none', borderRadius: 6,
                background: on ? 'var(--cream-200)' : 'transparent',
                color: 'var(--ink-900)', fontSize: 12.5, fontFamily: 'var(--font-ui)',
                fontWeight: on ? 700 : 400,
                cursor: 'pointer', textAlign: 'left',
              }}>
                <span style={{ color: 'var(--ink-500)', width: 14, fontWeight: on ? 700 : 500 }}>{SYM[o]}</span>{o}
                {on && <span style={{ marginLeft: 'auto', display: 'inline-flex' }}><Icon name="check" size={12} /></span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Chatbot FAB + panel ─────────────────────────────────
function ChatbotFab({ open, onOpen }) {
  return (
    <button onClick={onOpen} title="Ask your finance agent"
      className="fab-pulse"
      style={{
        position: 'absolute', bottom: 24, right: 24, zIndex: 30,
        width: 56, height: 56, borderRadius: 28,
        border: 'none', cursor: 'pointer',
        background: 'linear-gradient(135deg, #F4C430, #D97706)',
        color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'transform 180ms var(--ease)',
        transform: open ? 'scale(0.9)' : 'scale(1)',
      }}>
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3a9 9 0 0 1 9 9c0 5-4 9-9 9-1.3 0-2.5-.2-3.6-.7L3 21l1.3-4A8.9 8.9 0 0 1 3 12a9 9 0 0 1 9-9z"/>
        <circle cx="8.5" cy="12" r="1" fill="currentColor"/>
        <circle cx="12" cy="12" r="1" fill="currentColor"/>
        <circle cx="15.5" cy="12" r="1" fill="currentColor"/>
      </svg>
    </button>
  );
}

function ChatbotPanel({ open, onClose, currency }) {
  const [input, setInput] = React.useState('');
  const [msgs, setMsgs] = React.useState([
    { role: 'agent', text: "Hi! I'm MITA, your finance agent. I watch your spending and nudge you toward your goals. Ask me anything." },
    { role: 'agent', text: "Quick takes on this month:", chips: ['Show my top categories', 'Can I afford a $600 trip?', 'Set a coffee budget', 'Where am I bleeding cash?'] },
  ]);
  const [typing, setTyping] = React.useState(false);

  const send = (text) => {
    if (!text.trim()) return;
    setMsgs(m => [...m, { role: 'user', text }]);
    setInput('');
    setTyping(true);
    setTimeout(() => {
      setTyping(false);
      setMsgs(m => [...m, {
        role: 'agent',
        text: "Based on the last 30 days: Food is your biggest discretionary category ($412). If you cap eating out at $250/mo you'd save ~$160/mo — enough to cover that trip in under 4 months.",
        card: { label: 'Projected savings', value: 640, sub: 'next 4 months · at current rate' },
      }]);
    }, 900);
  };

  if (!open) return null;
  return (
    <div style={{
      position: 'absolute', bottom: 24, right: 24, zIndex: 31,
      width: 380, height: 520,
      background: 'var(--cream-50)', border: '1px solid var(--ink-200)',
      borderRadius: 16, boxShadow: '0 24px 60px -10px rgba(70,50,20,.35)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
      animation: 'slideUp 220ms var(--ease)',
    }}>
      <style>{`@keyframes slideUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}`}</style>
      {/* header */}
      <div style={{
        padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 10,
        background: 'linear-gradient(180deg, var(--cream-200), var(--cream-100))',
        borderBottom: '1px solid var(--ink-200)',
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: 17,
          background: 'linear-gradient(135deg, #F4C430, #D97706)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontFamily: 'var(--font-hand)', fontSize: 18, fontWeight: 700,
        }}>M</div>
        <div style={{ lineHeight: 1.2 }}>
          <div className="brand-hand" style={{ fontSize: 18, fontWeight: 700, color: 'var(--ink-900)' }}>MITA agent</div>
          <div style={{ fontSize: 10.5, color: 'var(--ink-500)', display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 6, height: 6, borderRadius: 3, background: 'var(--pos-500)' }}/>
            Watching · 247 records this month
          </div>
        </div>
        <div style={{ flex: 1 }} />
        <button onClick={onClose} style={{ border: 'none', background: 'transparent', cursor: 'pointer', width: 28, height: 28, borderRadius: 6, color: 'var(--ink-500)' }}>
          <Icon name="x" size={15} />
        </button>
      </div>

      {/* messages */}
      <div className="scroll-thin" style={{ flex: 1, overflow: 'auto', padding: '14px 12px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {msgs.map((m, i) => (
          <div key={i} style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '86%' }}>
            <div style={{
              padding: '9px 13px', borderRadius: m.role === 'user' ? '14px 14px 3px 14px' : '14px 14px 14px 3px',
              background: m.role === 'user' ? 'var(--ink-900)' : 'var(--cream-200)',
              color: m.role === 'user' ? 'var(--cream-50)' : 'var(--ink-900)',
              fontSize: 13, lineHeight: 1.55, fontFamily: 'var(--font-sans)',
            }}>{m.text}</div>
            {m.card && (
              <div style={{ marginTop: 6, padding: 12, borderRadius: 10, background: 'var(--cream-100)', border: '1px dashed var(--cream-400)' }}>
                <div style={{ fontSize: 10.5, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 0.8 }}>{m.card.label}</div>
                <div className="hand" style={{ fontSize: 26, fontWeight: 700, color: 'var(--pos-500)' }}>+{fmtMoney(m.card.value, currency)}</div>
                <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>{m.card.sub}</div>
              </div>
            )}
            {m.chips && (
              <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {m.chips.map(c => (
                  <button key={c} onClick={() => send(c)} style={{
                    padding: '5px 10px', borderRadius: 9999,
                    background: 'var(--cream-50)', border: '1px solid var(--ink-200)',
                    color: 'var(--ink-700)', fontSize: 11.5, cursor: 'pointer', fontFamily: 'var(--font-sans)',
                  }}>{c}</button>
                ))}
              </div>
            )}
          </div>
        ))}
        {typing && (
          <div style={{ alignSelf: 'flex-start' }}>
            <div style={{ padding: '9px 13px', borderRadius: '14px 14px 14px 3px', background: 'var(--cream-200)', display: 'flex', gap: 4 }}>
              {[0, 1, 2].map(i => <span key={i} style={{
                width: 6, height: 6, borderRadius: 3, background: 'var(--ink-400)',
                animation: `bounce 1.2s ${i * 0.15}s infinite`,
              }}/>)}
              <style>{`@keyframes bounce{0%,60%,100%{opacity:.3;transform:translateY(0)}30%{opacity:1;transform:translateY(-3px)}}`}</style>
            </div>
          </div>
        )}
      </div>

      {/* input */}
      <div style={{ padding: 10, borderTop: '1px solid var(--ink-200)', display: 'flex', gap: 6 }}>
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send(input)}
          placeholder="Ask MITA…"
          style={{
            flex: 1, height: 36, padding: '0 12px', borderRadius: 10,
            border: '1px solid var(--ink-200)', background: 'var(--cream-50)',
            fontSize: 13, fontFamily: 'var(--font-sans)', color: 'var(--ink-900)', outline: 'none',
          }}/>
        <button onClick={() => send(input)} style={{
          width: 36, height: 36, borderRadius: 10, border: 'none',
          background: 'var(--ink-900)', color: 'var(--cream-50)', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon name="arrow-up" size={15} />
        </button>
      </div>
    </div>
  );
}

Object.assign(window, { LeftSidebar, TopBar, IconBtn, SegmentedToggle, LanguagePicker, CurrencyPicker, ChatbotFab, ChatbotPanel });
