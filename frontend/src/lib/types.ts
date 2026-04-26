// Wire types — mirrors backend DTO shapes from design/PHASE_1.md §Data model.
// Backend serializes camelCase via Pydantic alias_generator=to_camel.

export type CategoryId = string; // slug, e.g. "food"

export interface Category {
  id: CategoryId;
  label: string;
  colorBg: string;
  colorDot: string;
  keywords: string[];
  autoAssign: boolean;
  sortOrder: number;
  createdAt: string;
}

export type CategoryCreate = Omit<Category, 'createdAt' | 'sortOrder'> & {
  sortOrder?: number;
};

export type CategoryUpdate = Partial<Omit<Category, 'id' | 'createdAt'>>;

export type TransactionSource = 'photo' | 'manual';

export interface RawMeta {
  imageUrl: string | null;
  ocrText: string | null;
  ocrEngine: string | null;
  llmModel: string | null;
}

export interface Transaction {
  id: string;
  occurredAt: string; // ISO 8601
  createdAt: string;
  merchant: string;
  amountCents: number; // negative = expense, positive = income
  currency: string;    // ISO 4217
  categoryId: CategoryId;
  source: TransactionSource;
  confidence: number | null;
  note: string | null;
  raw: RawMeta | null;
}

export type TransactionCreate = Omit<Transaction, 'id' | 'createdAt'>;
export type TransactionUpdate = Partial<TransactionCreate>;

export interface TransactionListResponse {
  data: Transaction[];
  nextCursor: string | null;
}

export interface ImportPhotoResponse {
  /** One draft per receipt extracted from the image. */
  previewTransactions: TransactionCreate[];
  /** Per-receipt overall confidence, parallel to previewTransactions. */
  confidences: number[];
  /** OCR text concatenated across all receipts in the image. */
  ocrText: string;
  ocrEngine: string;
  llmModel: string | null;
}

export interface Settings {
  profile: {
    fullName: string;
    preferredName: string;
    email: string;
    timezone: string;
    defaultCurrency: string;
  };
  appearance: {
    theme: 'light' | 'dark';
  };
  apiKeys: {
    openai?: string;
    anthropic?: string;
    google?: string;
    [k: string]: string | undefined;
  };
  import?: {
    /** When true, drafts above the confidence threshold are saved without
     *  showing a confirmation card. */
    quickImport?: boolean;
    /** 0..1; only drafts with overall confidence ≥ this are auto-saved. */
    confidenceThreshold?: number;
  };
  [k: string]: unknown;
}

export const QUICK_IMPORT_DEFAULTS = {
  quickImport: false,
  confidenceThreshold: 0.8,
} as const;

export interface Health {
  ok: boolean;
  version: string;
}
