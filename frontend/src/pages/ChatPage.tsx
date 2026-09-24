import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { fetchJson, streamChat } from '@/lib/api';
import { type ChatAction, type ChatHistory, type PlanProposalOperation, CHAT_INVALIDATION_KEYS } from '@/lib/chat';
import { fmtMoney } from '@/lib/formatters';
import { parseMoney } from '@/lib/budget';
import { useCategories } from '@/hooks/useCategories';
import { useLocale } from '@/lib/locale';
import { Button } from '@/components/ui/Button';
import { PaperCard } from '@/components/ui/PaperCard';
import { Icon } from '@/components/ui/Icon';
import { Modal } from '@/components/ui/Modal';
import financeIconUrl from '@/assets/finance_icon.png';

interface ChatSessionSummary {
  id: string;
  createdAt: string;
  title: string;
}

const actionLabels: Record<string, string> = {
  set_budget_item_limit: 'Category budget / 分类预算', set_planned_income: 'Planned income / 计划收入',
  set_savings_target: 'Savings target / 储蓄目标', add_quick_expense: 'Add expense / 添加支出',
  set_category_spend_total: 'Set spending total / 调整支出总额', clone_budget_plan: 'Copy plan / 复制预算',
  add_income: 'Add income / 添加收入', undo: 'Undo / 撤销',
  propose_next_week_budget: 'Next-week budget plan / 下周预算方案',
};

function PlanProposalCard({ action, busy, decide, edit }: {
  action: ChatAction; busy: boolean;
  decide: (id: string, decision: 'apply' | 'cancel') => void;
  edit: (id: string, operations: PlanProposalOperation[]) => Promise<void>;
}) {
  const categories = useCategories();
  const preview = action.payload.preview!;
  const operations = preview.operations ?? [];
  const totals = preview.totals!;
  const currency = preview.currency ?? '';
  const [editing, setEditing] = useState(false);
  const [amounts, setAmounts] = useState<Record<string, string>>({});
  const [editError, setEditError] = useState('');
  const statusLabels: Record<string, string> = { proposed: 'Awaiting confirmation · 等待确认', executed: 'Applied · 已执行', cancelled: 'Cancelled · 已取消', failed: 'Failed · 失败', confirmed: 'Applying · 执行中' };
  function beginEdit() {
    setAmounts(Object.fromEntries(operations.map(operation => [operation.category_id, String(operation.proposed_limit_cents / 100)])));
    setEditError('');
    setEditing(true);
  }
  async function saveEdit() {
    try {
      const updated = operations.map(operation => {
        const cents = parseMoney(amounts[operation.category_id] ?? '');
        if ((currency === 'JPY' || currency === 'KRW') && cents % 100) throw new Error(`${currency} requires whole currency units.`);
        return { ...operation, proposed_limit_cents: cents, delta_cents: cents - operation.previous_limit_cents };
      });
      await edit(action.id, updated);
      setEditing(false);
    } catch (error) {
      setEditError(error instanceof Error ? error.message : 'Could not update this proposal.');
    }
  }
  return <PaperCard className="space-y-4 !p-4">
    <div><p className="font-semibold">{actionLabels[action.actionType]}</p><p className="mt-1 text-sm text-ink-700">{preview.summary}</p></div>
    <div className="rounded-lg bg-cream-100 px-3 py-2 text-xs text-ink-700">
      <span className="font-medium">{preview.target_period?.starts_on} – {preview.target_period?.ends_on}</span>
      <span className="ml-2">· {preview.history_weeks_used ?? 0} history weeks</span>
    </div>
    <div className="divide-y divide-cream-200 rounded-xl border border-cream-200">
      {operations.map(operation => {
        const label = categories.data?.find(category => category.id === operation.category_id)?.label ?? operation.category_id;
        const delta = (editing ? parseMoneySafe(amounts[operation.category_id]) : operation.proposed_limit_cents) - operation.previous_limit_cents;
        const validDelta = Number.isFinite(delta);
        return <div key={operation.category_id} className="space-y-1.5 p-3 text-sm">
          <div className="flex items-center justify-between gap-3"><span className="font-medium">{label}<span className="ml-2 text-[10px] uppercase text-ink-500">{operation.kind}</span></span>
            {editing ? <input aria-label={`${label} proposed limit`} inputMode="decimal" value={amounts[operation.category_id] ?? ''} onChange={event => setAmounts(current => ({ ...current, [operation.category_id]: event.target.value }))} className="w-28 rounded-md border border-cream-300 bg-cream-50 px-2 py-1 text-right" /> : <span className="font-semibold">{fmtMoney(operation.proposed_limit_cents, currency)}</span>}
          </div>
          <div className="flex justify-between text-xs text-ink-500"><span>{fmtMoney(operation.previous_limit_cents, currency)} → {editing ? (validDelta ? fmtMoney(operation.previous_limit_cents + delta, currency) : '—') : fmtMoney(operation.proposed_limit_cents, currency)}</span><span className={validDelta && delta < 0 ? 'text-pos-500' : validDelta && delta > 0 ? 'text-neg-500' : ''}>{!validDelta ? 'Enter an amount' : delta === 0 ? 'No change' : `${delta > 0 ? '+' : ''}${fmtMoney(delta, currency)}`}</span></div>
          <p className="text-xs text-ink-500">{operation.reason}</p>
        </div>;
      })}
    </div>
    <dl className="grid grid-cols-2 gap-2 text-xs">
      <div><dt className="text-ink-500">Planned spend</dt><dd className="font-semibold">{fmtMoney(totals.proposed_planned_spend_cents, currency)}</dd></div>
      <div><dt className="text-ink-500">Previous plan</dt><dd>{fmtMoney(totals.previous_planned_spend_cents, currency)}</dd></div>
      {totals.planned_income_cents != null && <div><dt className="text-ink-500">Planned income</dt><dd>{fmtMoney(totals.planned_income_cents, currency)}</dd></div>}
      {totals.projected_residual_cents != null && <div><dt className="text-ink-500">Expected residual</dt><dd className="font-semibold">{fmtMoney(totals.projected_residual_cents, currency)}</dd></div>}
      {totals.savings_target_cents != null && <div><dt className="text-ink-500">Savings target</dt><dd>{fmtMoney(totals.savings_target_cents, currency)}</dd></div>}
    </dl>
    <p className="text-xs text-ink-500">{action.payload.undoneBy ? 'Undone · 已撤销' : action.payload.supersededBy ? 'Replaced by a newer proposal · 已被新方案替换' : statusLabels[action.status]}</p>
    {(editError || action.payload.error) && <p role="alert" className="text-sm text-neg-500">{editError || action.payload.error}</p>}
    {action.status === 'proposed' && (editing ? <div className="flex gap-2"><Button size="sm" disabled={busy} onClick={() => void saveEdit()}>Save proposal · 保存</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => setEditing(false)}>Back · 返回</Button></div> : <div className="flex gap-2"><Button size="sm" disabled={busy} onClick={() => decide(action.id, 'apply')}>Apply · 应用</Button><Button size="sm" variant="outline" disabled={busy} onClick={beginEdit}>Edit · 编辑</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => decide(action.id, 'cancel')}>Cancel · 取消</Button></div>)}
    {action.status === 'executed' && preview.target_period && <Link className="text-sm underline" to={`/?period=week&date=${preview.target_period.starts_on}`}>View budget · 查看预算 →</Link>}
  </PaperCard>;
}

function parseMoneySafe(value?: string): number {
  try { return parseMoney(value ?? ''); } catch { return Number.NaN; }
}

function ActionCard({ action, busy, decide, edit }: { action: ChatAction; busy: boolean; decide: (id: string, decision: 'apply' | 'cancel') => void; edit: (id: string, operations: PlanProposalOperation[]) => Promise<void> }) {
  const categories = useCategories();
  if (action.actionType === 'propose_next_week_budget' && action.payload.preview?.type === 'budget_plan_proposal') return <PlanProposalCard action={action} busy={busy} decide={decide} edit={edit} />;
  const p = action.payload.preview ?? action.payload.arguments ?? {};
  const amount = p.limit_cents ?? p.amount_cents ?? p.total_cents;
  const currency = String(p.currency ?? '');
  const category = categories.data?.find(c => c.id === p.category_id);
  const labels: Record<string, string> = { proposed: 'Awaiting confirmation · 等待确认', executed: 'Applied · 已执行', cancelled: 'Cancelled · 已取消', failed: 'Failed · 失败', confirmed: 'Applying · 执行中' };
  return <PaperCard className="space-y-3 !p-4">
    <p className="font-semibold">{actionLabels[action.actionType] ?? action.actionType}</p>
    <dl className="text-sm space-y-1">
      {p.category_id && <div><dt className="inline text-ink-500">Category · </dt><dd className="inline">{category?.label ?? String(p.category_id)}</dd></div>}
      {typeof amount === 'number' && <div><dt className="inline text-ink-500">Amount · </dt><dd className="inline font-semibold">{currency ? `${fmtMoney(amount, currency)} ${currency}` : amount / 100}</dd></div>}
      {typeof p.previous_cents === 'number' && <div className="text-ink-500">Previously · 原值 {fmtMoney(p.previous_cents, currency)} {currency}</div>}
      {p.starts_on && <div><dt className="inline text-ink-500">Period · </dt><dd className="inline">{String(p.starts_on)}{p.ends_on ? ` – ${p.ends_on}` : ''}</dd></div>}
      {p.occurred_on && <div>Date · {String(p.occurred_on)}</div>}
      {p.note && <div>{String(p.note)}</div>}
      {Array.isArray(p.items) && p.items.map(item => <div key={item.category_id}>{categories.data?.find(c => c.id === item.category_id)?.label ?? item.category_id} · {fmtMoney(item.limit_cents, currency)}</div>)}
      {typeof p.planned_income_cents === 'number' && <div>Planned income · {fmtMoney(p.planned_income_cents, currency)}</div>}
      {typeof p.savings_target_cents === 'number' && <div>Savings target · {fmtMoney(p.savings_target_cents, currency)}</div>}
    </dl>
    <p className="text-xs text-ink-500">{action.payload.undoneBy ? 'Undone · 已撤销' : labels[action.status]}</p>
    {action.payload.error && <p role="alert" className="text-sm text-neg-500">{action.payload.error}</p>}
    {action.status === 'proposed' && <div className="flex gap-2">
      <Button size="sm" disabled={busy} onClick={() => decide(action.id, 'apply')}>Apply · 应用</Button>
      <Button size="sm" variant="outline" disabled={busy} onClick={() => decide(action.id, 'cancel')}>Cancel · 取消</Button>
    </div>}
    {action.status === 'executed' && p.starts_on && p.period_type && <Link className="text-sm underline" to={`/?period=${p.period_type}&date=${p.starts_on}`}>View budget · 查看预算 →</Link>}
  </PaperCard>;
}

export function ChatPage() {
  const { sessionId = '' } = useParams();
  const navigate = useNavigate();
  const [draft, setDraft] = useState('');
  const [progress, setProgress] = useState('');
  const [renaming, setRenaming] = useState<ChatSessionSummary | null>(null);
  const [renameDraft, setRenameDraft] = useState('');
  const [deleting, setDeleting] = useState<ChatSessionSummary | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const qc = useQueryClient();
  const { locale } = useLocale();
  const zh = locale === 'zh';
  const sessions = useQuery({ queryKey: ['chat', 'sessions'],
    queryFn: () => fetchJson<ChatSessionSummary[]>('/api/chat/sessions') });
  const history = useQuery({ queryKey: ['chat', sessionId], enabled: !!sessionId,
    queryFn: () => fetchJson<ChatHistory>(`/api/chat/sessions/${sessionId}`) });
  async function refresh() {
    await Promise.all([qc.invalidateQueries({ queryKey: ['chat'] }), ...CHAT_INVALIDATION_KEYS.map(key => qc.invalidateQueries({ queryKey: [key] }))]);
  }
  function selectSession(id: string) {
    localStorage.setItem('mita-chat-session', id);
    navigate(`/chat/${id}`);
  }
  const create = useMutation({ mutationFn: () => fetchJson<{ id: string }>('/api/chat/sessions', { method: 'POST' }),
    onSuccess: async row => { selectSession(row.id); await qc.invalidateQueries({ queryKey: ['chat', 'sessions'] }); } });
  const rename = useMutation({ mutationFn: ({ id, title }: { id: string; title: string }) =>
    fetchJson<ChatSessionSummary>(`/api/chat/sessions/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  onSuccess: async () => { setRenaming(null); await qc.invalidateQueries({ queryKey: ['chat', 'sessions'] }); } });
  const remove = useMutation({ mutationFn: (id: string) =>
    fetchJson<void>(`/api/chat/sessions/${id}`, { method: 'DELETE' }),
  onSuccess: async (_, id) => {
    qc.removeQueries({ queryKey: ['chat', id] });
    if (localStorage.getItem('mita-chat-session') === id) localStorage.removeItem('mita-chat-session');
    if (sessionId === id) navigate('/chat', { replace: true });
    setDeleting(null);
    await qc.invalidateQueries({ queryKey: ['chat', 'sessions'] });
  } });
  const send = useMutation({ mutationFn: async (text: string) => {
    let id = sessionId;
    if (!id) { const row = await create.mutateAsync(); id = row.id; }
    setProgress(zh ? '正在读取预算…' : 'Reading your budget…');
    await streamChat(`/api/chat/sessions/${id}/stream`, text, event => {
      if (event.type === 'tool') setProgress(zh ? '正在读取预算服务…' : 'Reading budget services…');
    });
  }, onSuccess: () => setDraft(''), onSettled: async () => { setProgress(''); await refresh(); } });
  const decision = useMutation({ mutationFn: ({ id, choice }: { id: string; choice: 'apply' | 'cancel' }) =>
    fetchJson<ChatAction>(`/api/chat/sessions/${sessionId}/actions/${id}`, { method: 'POST', body: JSON.stringify({ decision: choice }) }), onSettled: refresh });
  const edit = useMutation({ mutationFn: ({ id, operations }: { id: string; operations: PlanProposalOperation[] }) =>
    fetchJson<ChatAction>(`/api/chat/sessions/${sessionId}/actions/${id}`, { method: 'PATCH', body: JSON.stringify({ operations: operations.map(operation => ({ categoryId: operation.category_id, proposedLimitCents: operation.proposed_limit_cents, reason: operation.reason, allowFixedReduction: operation.allow_fixed_reduction })) }) }), onSettled: refresh });
  const busy = send.isPending || decision.isPending || edit.isPending || create.isPending || rename.isPending || remove.isPending;
  useEffect(() => { input.current?.focus(); }, [sessionId]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [history.data, progress]);
  useEffect(() => {
    if (sessionId || !sessions.data) return;
    const saved = localStorage.getItem('mita-chat-session');
    if (saved && sessions.data.some(session => session.id === saved)) navigate(`/chat/${saved}`, { replace: true });
  }, [navigate, sessionId, sessions.data]);
  const error = send.error ?? decision.error ?? edit.error ?? create.error ?? rename.error ?? remove.error ?? history.error ?? sessions.error;
  const empty = !sessionId || !history.data?.messages.length;
  return <div className="flex h-dvh flex-col overflow-hidden bg-cream-100 text-ink-900 md:flex-row">
    <aside aria-label={zh ? '会话历史' : 'Chat history'} className="flex shrink-0 flex-col border-b border-cream-300 bg-cream-50/95 md:h-full md:w-72 md:border-b-0 md:border-r">
      <div className="flex items-center gap-2 border-b border-cream-200 p-3 md:block md:p-4">
        <Link to="/" className="flex min-w-0 items-center gap-2 rounded-lg px-2 py-2 text-sm font-medium text-ink-700 hover:bg-cream-200/70">
          <Icon name="chevronRight" size={16} className="rotate-180" />
          <span>{zh ? '返回看板' : 'Back to dashboard'}</span>
        </Link>
        <Button className="ml-auto md:mt-4 md:w-full" size="sm" disabled={busy} onClick={() => create.mutate()}>
          <Icon name="plus" size={15} /> {zh ? '新会话' : 'New chat'}
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-x-auto p-2 md:overflow-y-auto md:overflow-x-hidden">
        <p className="hidden px-2 pb-2 pt-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-500 md:block">{zh ? '历史会话' : 'History'}</p>
        <div className="flex gap-1 md:flex-col">
          {sessions.data?.map(session => <div key={session.id} className={`group flex w-64 shrink-0 items-center rounded-lg transition-colors md:w-full ${session.id === sessionId ? 'bg-cream-300' : 'hover:bg-cream-200/70'}`}>
            <button type="button" onClick={() => selectSession(session.id)} className="min-w-0 flex-1 px-3 py-2 text-left">
              <span className="block truncate text-sm font-medium">{session.title === 'New chat' && zh ? '新会话' : session.title}</span>
              <span className="mt-0.5 block text-[10px] text-ink-500">{new Date(session.createdAt).toLocaleDateString(locale)}</span>
            </button>
            <div className="flex pr-1 opacity-70 md:opacity-0 md:transition-opacity md:group-hover:opacity-100 md:group-focus-within:opacity-100">
              <button type="button" aria-label={zh ? `重命名 ${session.title}` : `Rename ${session.title}`} title={zh ? '重命名' : 'Rename'} onClick={() => { setRenaming(session); setRenameDraft(session.title === 'New chat' && zh ? '新会话' : session.title); }} className="rounded-md p-1.5 text-ink-500 hover:bg-cream-50 hover:text-ink-900"><Icon name="edit" size={14} /></button>
              <button type="button" aria-label={zh ? `删除 ${session.title}` : `Delete ${session.title}`} title={zh ? '删除' : 'Delete'} onClick={() => setDeleting(session)} className="rounded-md p-1.5 text-ink-500 hover:bg-neg-50 hover:text-neg-500"><Icon name="trash" size={14} /></button>
            </div>
          </div>)}
          {!sessions.isLoading && !sessions.data?.length && <p className="px-3 py-4 text-xs text-ink-500">{zh ? '还没有历史会话。' : 'No conversations yet.'}</p>}
        </div>
      </div>
    </aside>

    <main className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
      <header className="z-10 flex h-16 shrink-0 items-center border-b border-cream-200 bg-cream-100/90 px-4 backdrop-blur md:px-6">
        <div><h1 className="hand text-xl leading-tight">MITA</h1><p className="text-[11px] text-ink-500">{zh ? '预算，一起掌握。' : 'A little clarity for your budget.'}</p></div>
      </header>

      <div className="relative min-h-0 flex-1 overflow-hidden">
        <img src={financeIconUrl} alt="" aria-hidden="true" className="pointer-events-none absolute bottom-0 right-1 z-0 h-[62%] w-auto max-w-[52%] select-none object-contain object-bottom opacity-[0.14] sm:h-[74%] md:right-[2vw] md:h-[88%] md:max-h-[700px]" />
        <div className="relative z-10 h-full overflow-y-auto" aria-live="polite">
          <div className={`mx-auto flex min-h-full w-full max-w-3xl flex-col space-y-5 px-4 py-6 md:px-8 ${empty ? 'justify-center' : ''}`}>
          {empty && <div className="max-w-xl space-y-5 rounded-2xl bg-cream-100/80 py-4 backdrop-blur-[2px]">
            <div><h2 className="hand-body text-3xl text-ink-900">{zh ? '今天想看看哪一笔账？' : 'What should we look at today?'}</h2><p className="mt-2 text-sm leading-6 text-ink-500">{zh ? '可以从预算现状、最近支出或下周计划开始。自然语言修改会先让你确认。' : 'Start with budget status, recent spending, or a next-week plan. Natural-language changes need confirmation.'}</p></div>
            <div className="flex flex-wrap gap-2">
              {(zh ? [
                ['这个月预算怎么样？', '这个月预算怎么样？'], ['规划下周', '/plan next-week'],
                ['最近支出', '我最近花了什么？'], ['查看命令', '/help'],
              ] : [
                ['This month', 'How am I doing this month?'], ['Plan next week', '/plan next-week'],
                ['Recent spending', 'What did I spend recently?'], ['Commands', '/help'],
              ]).map(([label, prompt]) => <button key={label} type="button" onClick={() => { setDraft(prompt); input.current?.focus(); }} className="rounded-full border border-cream-300 bg-cream-50 px-3 py-1.5 text-xs hover:bg-cream-200">{label}</button>)}
            </div>
          </div>}
          {history.data?.messages.map(message => <div key={message.id} className="space-y-3">
            <div className={`whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${message.role === 'user' ? 'ml-auto max-w-[85%] bg-cream-300/80' : 'mr-auto max-w-[92%] border border-cream-200 bg-cream-50/95'}`}><p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-500">{message.role === 'user' ? (zh ? '你' : 'You') : 'MITA'}</p>{message.content}</div>
            {history.data.actions.filter(action => action.payload.messageId === message.id).map(action => <ActionCard key={action.id} action={action} busy={busy} decide={(id, choice) => decision.mutate({ id, choice })} edit={(id, operations) => edit.mutateAsync({ id, operations }).then(() => undefined)} />)}
          </div>)}
          {history.data?.actions.filter(action => !action.payload.messageId).map(action => <ActionCard key={action.id} action={action} busy={busy} decide={(id, choice) => decision.mutate({ id, choice })} edit={(id, operations) => edit.mutateAsync({ id, operations }).then(() => undefined)} />)}
          {progress && <p role="status" className="rounded-xl bg-cream-100/90 text-sm text-ink-500">{progress}</p>}
          {error && <div role="alert" className="rounded-xl bg-cream-100/90 text-sm text-neg-500">{error.message}<button className="ml-2 underline" onClick={() => void refresh()}>{zh ? '刷新' : 'Refresh'}</button></div>}
            <div ref={bottom} />
          </div>
        </div>
      </div>

      <form className="relative z-10 shrink-0 border-t border-cream-200 bg-cream-100/95 px-4 py-3 backdrop-blur md:px-8" onSubmit={event => { event.preventDefault(); if (draft.trim() && !busy) send.mutate(draft.trim()); }}>
        <div className="mx-auto max-w-3xl rounded-2xl border border-cream-300 bg-cream-50 p-2 shadow-sm focus-within:ring-2 focus-within:ring-ink-900/10">
          <textarea ref={input} aria-label="Message MITA" maxLength={8000} rows={2} value={draft} disabled={busy} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); if (draft.trim() && !busy) send.mutate(draft.trim()); } }} className="w-full resize-none bg-transparent px-2 py-1 text-sm leading-6 outline-none" placeholder={zh ? '询问预算，或输入 /summary month' : 'Ask about your budget, or /summary month'} />
          <div className="flex items-center justify-between gap-3 px-1"><span className="truncate text-[10px] text-ink-500">/plan · /summary · /spend · /budget · /undo · /help</span><Button size="sm" type="submit" disabled={busy || !draft.trim()}>{zh ? '发送' : 'Send'}</Button></div>
        </div>
      </form>
    </main>

    <Modal open={renaming !== null} onClose={() => setRenaming(null)} title={zh ? '重命名会话' : 'Rename conversation'} size="sm" footer={<>
      <Button variant="ghost" onClick={() => setRenaming(null)} disabled={rename.isPending}>{zh ? '取消' : 'Cancel'}</Button>
      <Button onClick={() => { if (renaming && renameDraft.trim()) rename.mutate({ id: renaming.id, title: renameDraft.trim() }); }} disabled={rename.isPending || !renameDraft.trim()}>{zh ? '保存' : 'Save'}</Button>
    </>}>
      <label className="block text-sm font-medium text-ink-700">{zh ? '会话名称' : 'Conversation name'}
        <input autoFocus maxLength={80} value={renameDraft} onChange={event => setRenameDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && renaming && renameDraft.trim()) rename.mutate({ id: renaming.id, title: renameDraft.trim() }); }} className="mt-2 w-full rounded-lg border border-cream-300 bg-cream-100 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ink-900/15" />
      </label>
    </Modal>

    <Modal open={deleting !== null} onClose={() => setDeleting(null)} title={zh ? '删除会话？' : 'Delete conversation?'} size="sm" footer={<>
      <Button variant="ghost" onClick={() => setDeleting(null)} disabled={remove.isPending}>{zh ? '保留' : 'Keep'}</Button>
      <Button variant="danger" onClick={() => { if (deleting) remove.mutate(deleting.id); }} disabled={remove.isPending}>{zh ? '删除' : 'Delete'}</Button>
    </>}>
      <p className="text-sm leading-6 text-ink-700">{zh ? '此会话中的消息和操作记录都会被永久删除。' : 'Messages and action records in this conversation will be permanently deleted.'}</p>
    </Modal>
  </div>;
}
