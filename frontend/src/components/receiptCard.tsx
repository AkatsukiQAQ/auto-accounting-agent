import * as React from 'react';

interface ReceiptCardProps {
  merchantName?: string | null;
  category?: string | null;
  amount?: number | null;
  currency?: string | null;   // e.g. JPY / USD
  dateTime?: string | Date | null;
  rawText: string;
}

export function receiptCard({
  merchantName = null,
  category = null,
  amount = null,
  currency = null,
  dateTime = null,
  rawText
}: ReceiptCardProps) {
  const dt = typeof dateTime === 'string'? new Date(dateTime): dateTime;
  // TODO
}