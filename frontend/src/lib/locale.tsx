import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

export type Locale = 'en' | 'zh' | 'ja';

const messages: Record<Locale, Record<string, string>> = {
  en: {
    'nav.group.budget': 'Budget', 'nav.group.activity': 'Activity', 'nav.group.system': 'System',
    'nav.chat': 'Chat', 'nav.dashboard': 'Dashboard', 'nav.plan': 'Plan', 'nav.records': 'Records', 'nav.import': 'Import', 'nav.categories': 'Categories', 'nav.settings': 'Settings',
    'brand.tagline': 'Your finance assistant', 'search.placeholder': 'Search records, categories…', 'search.label': 'Search (coming in a later phase)',
    'dashboard.eyebrow': 'A little clarity for your everyday', 'dashboard.subtitle': 'What you planned, what you spent, what remains.', 'dashboard.quickExpense': '+ Quick expense',
    'dashboard.available': 'Available to spend · this {period}', 'dashboard.adjustPlan': 'Adjust plan →', 'dashboard.spentOf': 'Spent {spent} of {planned} · {days} days left',
    'dashboard.safe': 'Safe flexible spend', 'dashboard.perDay': '/ day', 'dashboard.safeHint': 'A gentle daily guide from the remaining flexible budget.',
    'dashboard.attention': 'Needs your attention', 'dashboard.onTrack': 'Your recorded spending is within plan so far.', 'dashboard.over': 'Over budget', 'dashboard.ahead': 'Ahead of pace', 'dashboard.left': '{amount} left', 'dashboard.notAllocated': 'Not allocated', 'dashboard.addPlan': 'Add it to your plan',
    'dashboard.mix': 'Spending mix', 'dashboard.mixHint': 'Recorded spending by category.', 'dashboard.noSpend': 'No spending recorded for this period yet.',
    'dashboard.budgets': 'Category budgets', 'dashboard.budgetHint': 'A quick color check shows what needs attention.', 'dashboard.setTotal': 'Set category total', 'dashboard.noAllocated': 'No categories allocated yet.', 'dashboard.addCategories': 'Add category budgets',
    'dashboard.recent': 'Recent records', 'dashboard.viewAll': 'View all →', 'dashboard.loadingBudget': 'Could not load your budget. Please retry.',
    'period.week': 'week', 'period.month': 'month', 'dashboard.createTitle': 'Make room for what matters.', 'dashboard.createHint': 'Create a {period} plan in {currency} to see your spending against it. Existing records will count automatically.', 'dashboard.createPlan': 'Create a plan', 'dashboard.quickTitle': 'Quick expense', 'dashboard.totalTitle': 'Set category total',
    'period.weekLabel': 'Week', 'period.monthLabel': 'Month', 'period.previous': 'Previous period', 'period.next': 'Next period',
    'status.safe': 'On track', 'status.watch': 'Watch', 'status.warning': 'Near limit', 'status.over': 'Over budget',
  },
  zh: {
    'nav.group.budget': '预算', 'nav.group.activity': '收支', 'nav.group.system': '系统',
    'nav.chat': '会话', 'nav.dashboard': '看板', 'nav.plan': '预算计划', 'nav.records': '记录', 'nav.import': '导入', 'nav.categories': '分类', 'nav.settings': '设置',
    'brand.tagline': '你的财务助手', 'search.placeholder': '搜索记录、分类…', 'search.label': '搜索（后续阶段提供）',
    'dashboard.eyebrow': '给日常多一点清晰感', 'dashboard.subtitle': '计划了多少、花了多少、还剩多少。', 'dashboard.quickExpense': '+ 快速记账',
    'dashboard.available': '本{period}可支配金额', 'dashboard.adjustPlan': '调整计划 →', 'dashboard.spentOf': '已花 {spent} / 预算 {planned} · 还剩 {days} 天',
    'dashboard.safe': '灵活支出建议', 'dashboard.perDay': '/ 天', 'dashboard.safeHint': '基于剩余灵活预算计算的每日温和参考。',
    'dashboard.attention': '需要留意', 'dashboard.onTrack': '目前记录的支出仍在计划内。', 'dashboard.over': '已超预算', 'dashboard.ahead': '支出偏快', 'dashboard.left': '剩余 {amount}', 'dashboard.notAllocated': '未分配', 'dashboard.addPlan': '纳入预算计划',
    'dashboard.mix': '花费构成', 'dashboard.mixHint': '按分类查看本期已记录支出。', 'dashboard.noSpend': '本期还没有记录支出。',
    'dashboard.budgets': '分类预算', 'dashboard.budgetHint': '通过颜色和圆环快速识别需要关注的项目。', 'dashboard.setTotal': '设置分类总额', 'dashboard.noAllocated': '还没有分类预算。', 'dashboard.addCategories': '添加分类预算',
    'dashboard.recent': '最近记录', 'dashboard.viewAll': '查看全部 →', 'dashboard.loadingBudget': '无法加载预算，请重试。',
    'period.week': '周', 'period.month': '月', 'dashboard.createTitle': '给真正重要的事留出空间。', 'dashboard.createHint': '创建一个 {currency} {period}预算计划，即可将已有记录自动计入预算。', 'dashboard.createPlan': '创建预算计划', 'dashboard.quickTitle': '快速记账', 'dashboard.totalTitle': '设置分类总额',
    'period.weekLabel': '周', 'period.monthLabel': '月', 'period.previous': '上一期', 'period.next': '下一期',
    'status.safe': '正常', 'status.watch': '留意', 'status.warning': '接近上限', 'status.over': '已超预算',
  },
  ja: {
    'nav.group.budget': '予算', 'nav.group.activity': '収支', 'nav.group.system': 'システム',
    'nav.chat': 'チャット', 'nav.dashboard': 'ダッシュボード', 'nav.plan': '予算プラン', 'nav.records': '記録', 'nav.import': '取込', 'nav.categories': 'カテゴリ', 'nav.settings': '設定',
    'brand.tagline': 'あなたの家計アシスタント', 'search.placeholder': '記録・カテゴリを検索…', 'search.label': '検索（今後のフェーズで対応）',
    'dashboard.eyebrow': '毎日に、少しの見通しを', 'dashboard.subtitle': '計画・支出・残額をひと目で。', 'dashboard.quickExpense': '+ 支出を追加',
    'dashboard.available': '今{period}使える金額', 'dashboard.adjustPlan': 'プランを調整 →', 'dashboard.spentOf': '{spent} / {planned} を支出 · 残り{days}日',
    'dashboard.safe': '柔軟費の目安', 'dashboard.perDay': '/ 日', 'dashboard.safeHint': '残りの柔軟予算から計算した、1日あたりの穏やかな目安です。',
    'dashboard.attention': '確認が必要です', 'dashboard.onTrack': '記録済みの支出は、今のところプラン内です。', 'dashboard.over': '予算オーバー', 'dashboard.ahead': 'ペースが速め', 'dashboard.left': '残り {amount}', 'dashboard.notAllocated': '未配分', 'dashboard.addPlan': 'プランに追加',
    'dashboard.mix': '支出の内訳', 'dashboard.mixHint': '記録済み支出をカテゴリ別に表示。', 'dashboard.noSpend': 'この期間の支出はまだ記録されていません。',
    'dashboard.budgets': 'カテゴリ予算', 'dashboard.budgetHint': '色と円環で注意が必要な項目を確認できます。', 'dashboard.setTotal': 'カテゴリ合計を設定', 'dashboard.noAllocated': 'カテゴリ予算はまだありません。', 'dashboard.addCategories': 'カテゴリ予算を追加',
    'dashboard.recent': '最近の記録', 'dashboard.viewAll': 'すべて表示 →', 'dashboard.loadingBudget': '予算を読み込めませんでした。再試行してください。',
    'period.week': '週間', 'period.month': '月間', 'dashboard.createTitle': '大切なことのために、余白を。', 'dashboard.createHint': '{currency}で{period}プランを作成すると、記録済みの支出を予算と比較できます。', 'dashboard.createPlan': 'プランを作成', 'dashboard.quickTitle': '支出を追加', 'dashboard.totalTitle': 'カテゴリ合計を設定',
    'period.weekLabel': '週', 'period.monthLabel': '月', 'period.previous': '前の期間', 'period.next': '次の期間',
    'status.safe': '順調', 'status.watch': '要確認', 'status.warning': '上限間近', 'status.over': '予算オーバー',
  },
};

const LocaleContext = createContext<{ locale: Locale; setLocale: (locale: Locale) => void; t: (key: string, values?: Record<string, string | number>) => string } | null>(null);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(() => {
    const saved = localStorage.getItem('mita-locale');
    return saved === 'zh' || saved === 'ja' ? saved : 'en';
  });
  useEffect(() => { localStorage.setItem('mita-locale', locale); document.documentElement.lang = locale; }, [locale]);
  const value = useMemo(() => ({ locale, setLocale, t: (key: string, values: Record<string, string | number> = {}) =>
    (messages[locale][key] ?? messages.en[key] ?? key).replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? `{${name}}`)) }), [locale]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

// Context hooks intentionally live beside the provider in this small locale module.
// eslint-disable-next-line react-refresh/only-export-components
export function useLocale() {
  const value = useContext(LocaleContext);
  if (!value) throw new Error('useLocale must be used within LocaleProvider');
  return value;
}
