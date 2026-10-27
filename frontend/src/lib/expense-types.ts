export type ExpenseShare = {
  user_id: number;
  username: string;
  amount_minor: number;
};
export type Expense = {
  id: number;
  title: string;
  expense_date: string;
  category: string;
  currency: string;
  amount_minor: number;
  payer_id: number;
  payer_name: string;
  split_mode: "equal" | "custom";
  shares: ExpenseShare[];
  activity_id: number | null;
  notes: string | null;
  created_by: number;
  created_at: string;
};
export type Settlement = {
  id: number;
  sender_id: number;
  sender_name: string;
  recipient_id: number;
  recipient_name: string;
  amount_minor: number;
  currency: string;
  settled_on: string;
  notes: string | null;
  created_by: number;
};
export type Balance = {
  user_id: number;
  username: string;
  active: boolean;
  paid_minor: number;
  owed_minor: number;
  balance_minor: number;
};
export type Ledger = {
  currency: string;
  minor_digits: number;
  total_minor: number;
  expenses: Expense[];
  settlements: Settlement[];
  balances: Balance[];
  suggestions: {
    sender_id: number;
    recipient_id: number;
    amount_minor: number;
  }[];
};
export type ExpenseValues = {
  title: string;
  expense_date: string;
  category: string;
  amount: string;
  payer_id: string;
  split_mode: string;
  participant_ids: string[];
  custom: Record<string, string>;
  activity_id: string;
  notes: string;
};
export type ExpenseFormState = { values: ExpenseValues; error?: string };
export type SettlementValues = {
  sender_id: string;
  recipient_id: string;
  amount: string;
  settled_on: string;
  notes: string;
};
export type SettlementFormState = { values: SettlementValues; error?: string };
export const expenseCategories: Record<string, string> = {
  lodging: "住宿",
  transport: "交通",
  food: "餐飲",
  tickets: "門票",
  shopping: "購物",
  other: "其他",
};
