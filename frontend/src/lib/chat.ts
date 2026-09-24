export interface ChatAction {
  id: string;
  actionType: string;
  status: 'proposed' | 'confirmed' | 'executed' | 'cancelled' | 'failed';
  payload: {
    arguments?: Record<string, string | number | null>;
    preview?: {
      type?: 'budget_plan_proposal';
      category_id?: string; currency?: string; limit_cents?: number; amount_cents?: number; total_cents?: number;
      previous_cents?: number | null; starts_on?: string; ends_on?: string; period_type?: string;
      occurred_on?: string; note?: string | null; planned_income_cents?: number | null; savings_target_cents?: number | null;
      items?: { category_id: string; limit_cents: number }[];
      target_period?: { period_type: 'week'; starts_on: string; ends_on: string };
      summary?: string;
      operations?: PlanProposalOperation[];
      totals?: PlanProposalTotals;
      history_weeks_used?: number;
    };
    messageId?: string;
    error?: string;
    undoneBy?: string;
    supersededBy?: string;
  };
}
export interface PlanProposalOperation {
  category_id: string;
  kind: 'fixed' | 'flexible' | 'discretionary';
  previous_limit_cents: number;
  proposed_limit_cents: number;
  delta_cents: number;
  reason: string;
  allow_fixed_reduction: boolean;
}
export interface PlanProposalTotals {
  previous_planned_spend_cents: number;
  proposed_planned_spend_cents: number;
  planned_income_cents: number | null;
  savings_target_cents: number | null;
  projected_residual_cents: number | null;
}
export interface ChatMessage { id: string; role: 'user' | 'assistant'; content: string }
export interface ChatHistory { messages: ChatMessage[]; actions: ChatAction[] }
export type ChatEvent = { type: 'tool'; name: string } | { type: 'error'; message: string } |
  { type: 'done'; message: ChatMessage; action: ChatAction | null };

export const CHAT_INVALIDATION_KEYS = ['budgets', 'transactions', 'accounts'] as const;

/** Framed events may span arbitrary UTF-8 network chunks. */
export function parseChatLines(buffer: string): { events: ChatEvent[]; rest: string } {
  const lines = buffer.split('\n');
  const rest = lines.pop() ?? '';
  return { events: lines.filter(line => line.trim()).map(line => JSON.parse(line) as ChatEvent), rest };
}
