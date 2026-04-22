// App shell — composes chrome + current screen + chatbot per variant

function AppShell({ variant, currency, setCurrency, theme, setTheme, lang, setLang, showChrome = true }) {
  const [active, setActive] = React.useState('dashboard');
  const [collapsed, setCollapsed] = React.useState(false);
  const [chatOpen, setChatOpen] = React.useState(false);

  const screens = {
    dashboard: variant === 'A' ? <DashboardA currency={currency}/>
              : variant === 'B' ? <DashboardB currency={currency}/>
              : <DashboardC currency={currency}/>,
    records:    <RecordsScreen currency={currency}/>,
    import:     <ImportScreen currency={currency}/>,
    budget:     <BudgetScreen currency={currency}/>,
    categories: <CategoriesScreen/>,
  };

  return (
    <div data-theme={theme} className="paper-bg" style={{
      position: 'absolute', inset: 0, display: 'flex',
      fontFamily: 'var(--font-sans)', color: 'var(--ink-900)', overflow: 'hidden',
    }}>
      {showChrome && <LeftSidebar active={active} onNav={setActive} collapsed={collapsed} onToggle={() => setCollapsed(c => !c)} variant={variant}/>}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, position: 'relative' }}>
        {showChrome && <TopBar currency={currency} onCurrency={setCurrency} theme={theme} onTheme={setTheme} lang={lang} onLang={setLang} variant={variant}/>}
        {screens[active]}
        <ChatbotFab open={chatOpen} onOpen={() => setChatOpen(o => !o)}/>
        <ChatbotPanel open={chatOpen} onClose={() => setChatOpen(false)} currency={currency}/>
      </div>
    </div>
  );
}

// Artboard wrapper that owns its own state (each DCArtboard renders one)
function Artboard({ variant, defaultScreen = 'dashboard', defaultTheme = 'light', defaultLang = 'en' }) {
  const [currency, setCurrency] = React.useState('USD');
  const [theme, setTheme] = React.useState(defaultTheme);
  const [lang, setLang] = React.useState(defaultLang);
  const [active, setActive] = React.useState(defaultScreen);
  const [collapsed, setCollapsed] = React.useState(false);
  const [chatOpen, setChatOpen] = React.useState(defaultScreen === 'chat');
  // Preferred name — empty = fall back to account first name
  const [accountName, setAccountName] = React.useState('Lena Chen');
  const [preferredName, setPreferredName] = React.useState('');
  const accountFirst = (accountName || '').trim().split(/\s+/)[0] || '';
  const displayName = preferredName.trim() || accountFirst;

  const screens = {
    dashboard: variant === 'A' ? <DashboardA currency={currency}/>
              : variant === 'B' ? <DashboardB currency={currency}/>
              : <DashboardC currency={currency}/>,
    records:    <RecordsScreen currency={currency}/>,
    import:     <ImportScreen currency={currency}/>,
    budget:     <BudgetScreen currency={currency}/>,
    categories: <CategoriesScreen/>,
    settings:   <SettingsScreen currency={currency} theme={theme} setTheme={setTheme} lang={lang} setLang={setLang} preferredName={preferredName} setPreferredName={setPreferredName} accountName={accountName} setAccountName={setAccountName}/>,
    chat:       variant === 'A' ? <DashboardA currency={currency}/>
              : variant === 'B' ? <DashboardB currency={currency}/>
              : <DashboardC currency={currency}/>,
  };

  return (
    <I18NProvider lang={lang} name={displayName}>
      <div data-theme={theme} lang={lang} className="paper-bg" style={{
        position: 'absolute', inset: 0, display: 'flex',
        fontFamily: 'var(--font-sans)', color: 'var(--ink-900)', overflow: 'hidden',
      }}>
        <LeftSidebar active={active === 'chat' ? 'dashboard' : active} onNav={setActive} collapsed={collapsed} onToggle={() => setCollapsed(c => !c)} variant={variant}/>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, position: 'relative' }}>
          <TopBar currency={currency} onCurrency={setCurrency} theme={theme} onTheme={setTheme} lang={lang} onLang={setLang} variant={variant}/>
          {screens[active]}
          <ChatbotFab open={chatOpen} onOpen={() => setChatOpen(o => !o)}/>
          <ChatbotPanel open={chatOpen} onClose={() => setChatOpen(false)} currency={currency}/>
        </div>
      </div>
    </I18NProvider>
  );
}

function App() {
  // Tweak: handMode — "hand" (headings hand / body sans) or "full" (all Kalam)
  const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
    "handMode": "hand"
  }/*EDITMODE-END*/;
  const [tweaks, setTweaks] = React.useState(TWEAK_DEFAULTS);
  const [tweaksOpen, setTweaksOpen] = React.useState(false);

  React.useEffect(() => {
    const onMsg = (e) => {
      if (!e.data) return;
      if (e.data.type === '__activate_edit_mode') setTweaksOpen(true);
      if (e.data.type === '__deactivate_edit_mode') setTweaksOpen(false);
    };
    window.addEventListener('message', onMsg);
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    return () => window.removeEventListener('message', onMsg);
  }, []);

  React.useEffect(() => {
    // Apply handmode by stamping attribute on <html> so tokens cascade everywhere
    document.documentElement.setAttribute('data-handmode', tweaks.handMode);
  }, [tweaks.handMode]);

  const update = (patch) => {
    setTweaks(t => ({ ...t, ...patch }));
    window.parent.postMessage({ type: '__edit_mode_set_keys', edits: patch }, '*');
  };

  return (
    <>
      <DesignCanvas>
      <DCSection id="dashboards" title="Dashboard · three directions" subtitle="Same data, different voices. Click any artboard to open fullscreen.">
        <DCArtboard id="a" label="A · Classic ledger" width={1280} height={840}>
          <Artboard variant="A"/>
        </DCArtboard>
        <DCArtboard id="b" label="B · Journal · handwritten" width={1280} height={840}>
          <Artboard variant="B"/>
        </DCArtboard>
        <DCArtboard id="c" label="C · Control room" width={1280} height={840}>
          <Artboard variant="C"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="dark" title="Dark mode" subtitle="Same three variants with theme='dark'. Use the sun/moon icon in the topbar to toggle at runtime.">
        <DCArtboard id="a-dark" label="A · dark" width={1280} height={840}>
          <Artboard variant="A" defaultTheme="dark"/>
        </DCArtboard>
        <DCArtboard id="b-dark" label="B · dark" width={1280} height={840}>
          <Artboard variant="B" defaultTheme="dark"/>
        </DCArtboard>
        <DCArtboard id="c-dark" label="C · dark" width={1280} height={840}>
          <Artboard variant="C" defaultTheme="dark"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="supporting" title="Supporting screens" subtitle="Detail records · Import · Budget & goals. Chrome is shared across all three dashboard variants.">
        <DCArtboard id="records" label="Records · detail view" width={1280} height={840}>
          <Artboard variant="A" defaultScreen="records"/>
        </DCArtboard>
        <DCArtboard id="import"  label="Import · screenshot & manual" width={1280} height={840}>
          <Artboard variant="A" defaultScreen="import"/>
        </DCArtboard>
        <DCArtboard id="budget"  label="Budget & goals · settings" width={1280} height={840}>
          <Artboard variant="A" defaultScreen="budget"/>
        </DCArtboard>
        <DCArtboard id="categories" label="Categories · classification" width={1280} height={840}>
          <Artboard variant="A" defaultScreen="categories"/>
        </DCArtboard>
        <DCArtboard id="settings" label="Settings · pipeline & API keys" width={1280} height={1200}>
          <Artboard variant="A" defaultScreen="settings"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="chat" title="Chatbot agent" subtitle="Tap the orange FAB in any artboard's bottom-right to open the panel.">
        <DCArtboard id="chat-open" label="Agent panel · open" width={1280} height={840}>
          <Artboard variant="A" defaultScreen="chat"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="locales" title="Localization · 日本語 · 中文" subtitle="All three dashboards in Japanese and Simplified Chinese. CJK uses Klee One (JA) / Ma Shan Zheng (ZH) for the handwritten accents.">
        <DCArtboard id="a-ja" label="A · 日本語" width={1280} height={840}>
          <Artboard variant="A" defaultLang="ja"/>
        </DCArtboard>
        <DCArtboard id="b-ja" label="B · 日本語 · ジャーナル" width={1280} height={840}>
          <Artboard variant="B" defaultLang="ja"/>
        </DCArtboard>
        <DCArtboard id="c-ja" label="C · 日本語 · コントロール" width={1280} height={840}>
          <Artboard variant="C" defaultLang="ja"/>
        </DCArtboard>
        <DCArtboard id="a-zh" label="A · 中文" width={1280} height={840}>
          <Artboard variant="A" defaultLang="zh"/>
        </DCArtboard>
        <DCArtboard id="b-zh" label="B · 中文 · 日志" width={1280} height={840}>
          <Artboard variant="B" defaultLang="zh"/>
        </DCArtboard>
        <DCArtboard id="c-zh" label="C · 中文 · 控制台" width={1280} height={840}>
          <Artboard variant="C" defaultLang="zh"/>
        </DCArtboard>
      </DCSection>
    </DesignCanvas>

    {tweaksOpen && (
      <div style={{
        position: 'fixed', bottom: 20, right: 20, zIndex: 9999,
        width: 280, padding: 16, borderRadius: 14,
        background: 'var(--cream-50)', border: '1px solid var(--ink-200)',
        boxShadow: '0 16px 40px rgba(0,0,0,.18)',
        fontFamily: 'var(--font-ui)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <div className="hand" style={{ fontSize: 22, color: 'var(--ink-900)', fontWeight: 700 }}>Tweaks</div>
          <div style={{ flex: 1 }}/>
          <button onClick={() => setTweaksOpen(false)} style={{
            border: 'none', background: 'transparent', cursor: 'pointer',
            color: 'var(--ink-500)', fontSize: 18, lineHeight: 1,
          }}>×</button>
        </div>
        <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--ink-500)', marginBottom: 6 }}>Handwritten extent</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {[
            { id: 'hand', label: 'Accents only (Kalam headings, sans body)', sub: 'Recommended · readable' },
            { id: 'full', label: 'Full Kalam (everything handwritten)',      sub: 'Warmer · denser to read' },
          ].map(o => {
            const on = tweaks.handMode === o.id;
            return (
              <button key={o.id} onClick={() => update({ handMode: o.id })} style={{
                display: 'block', textAlign: 'left', padding: '10px 12px',
                borderRadius: 10, cursor: 'pointer',
                border: on ? '1.5px solid var(--ink-900)' : '1px solid var(--ink-200)',
                background: on ? 'var(--cream-200)' : 'var(--cream-50)',
                color: 'var(--ink-900)', fontFamily: 'var(--font-ui)',
              }}>
                <div style={{ fontSize: 12.5, fontWeight: on ? 700 : 500 }}>{o.label}</div>
                <div style={{ fontSize: 10.5, color: 'var(--ink-500)', marginTop: 2 }}>{o.sub}</div>
              </button>
            );
          })}
        </div>
      </div>
    )}
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
