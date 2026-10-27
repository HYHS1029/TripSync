"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { isTripId, TripApiError, tripRequest } from "@/lib/trips";
import { parseMinor } from "@/lib/money";
import type {
  ExpenseFormState,
  ExpenseValues,
  Ledger,
  SettlementFormState,
} from "@/lib/expense-types";
import type { MutationState } from "@/lib/trip-types";

function read(form: FormData, name: string) {
  const value = form.get(name);
  return typeof value === "string" ? value.trim() : "";
}
function errorMessage(error: unknown) {
  if (error instanceof TripApiError) {
    if (error.status === 401) redirect("/login");
    if (error.status === 403)
      return "只有這筆紀錄的建立者或旅程擁有者可以修改。";
    if (error.status === 404) return "紀錄已不存在，或你已無法存取這趟旅程。";
    if (error.status === 409)
      return "餘額或資料已變動、還款超過未結清金額，或已達紀錄上限。請重新整理後確認。";
    if (error.status === 422)
      return "請確認金額、分攤總和、日期及所選成員／活動。";
  }
  return "暫時無法儲存，請稍後重試。";
}
export async function saveExpense(
  tripId: number,
  expenseId: number | null,
  _state: ExpenseFormState,
  form: FormData,
): Promise<ExpenseFormState> {
  const participants = form
    .getAll("participant_ids")
    .filter((value): value is string => typeof value === "string");
  const values: ExpenseValues = {
    title: read(form, "title"),
    expense_date: read(form, "expense_date"),
    category: read(form, "category"),
    amount: read(form, "amount"),
    payer_id: read(form, "payer_id"),
    split_mode: read(form, "split_mode"),
    participant_ids: participants,
    custom: Object.fromEntries(
      participants.map((id) => [id, read(form, `share_${id}`)]),
    ),
    activity_id: read(form, "activity_id"),
    notes: read(form, "notes"),
  };
  if (!isTripId(tripId) || (expenseId !== null && !isTripId(expenseId)))
    return { values, error: "找不到旅程或費用。" };
  try {
    const ledger = await tripRequest<Ledger>(`/trips/${tripId}/ledger`);
    const amount = parseMinor(values.amount, ledger.minor_digits);
    if (amount === null || amount <= 0)
      return {
        values,
        error: `請輸入正確金額，${ledger.currency} 最多 ${ledger.minor_digits} 位小數。`,
      };
    const shares = participants.map((id) => ({
      user_id: Number(id),
      amount_minor: parseMinor(values.custom[id], ledger.minor_digits),
    }));
    if (
      values.split_mode === "custom" &&
      shares.some((share) => share.amount_minor === null)
    )
      return { values, error: "請為每位分攤成員填入有效金額，可填 0。" };
    await tripRequest(
      `/trips/${tripId}/expenses${expenseId === null ? "" : `/${expenseId}`}`,
      {
        method: expenseId === null ? "POST" : "PUT",
        body: JSON.stringify({
          title: values.title,
          expense_date: values.expense_date,
          category: values.category,
          amount_minor: amount,
          payer_id: Number(values.payer_id),
          split_mode: values.split_mode,
          participant_ids: participants.map(Number),
          custom_shares: values.split_mode === "custom" ? shares : [],
          activity_id: values.activity_id ? Number(values.activity_id) : null,
          notes: values.notes || null,
        }),
      },
    );
  } catch (error) {
    return { values, error: errorMessage(error) };
  }
  revalidatePath(`/trips/${tripId}/expenses`);
  redirect(`/trips/${tripId}/expenses`);
}
export async function saveSettlement(
  tripId: number,
  _state: SettlementFormState,
  form: FormData,
): Promise<SettlementFormState> {
  const values = {
    sender_id: read(form, "sender_id"),
    recipient_id: read(form, "recipient_id"),
    amount: read(form, "amount"),
    settled_on: read(form, "settled_on"),
    notes: read(form, "notes"),
  };
  if (!isTripId(tripId)) return { values, error: "找不到旅程。" };
  try {
    const ledger = await tripRequest<Ledger>(`/trips/${tripId}/ledger`);
    const amount = parseMinor(values.amount, ledger.minor_digits);
    if (amount === null || amount <= 0)
      return {
        values,
        error: `請輸入有效的正數金額，最多 ${ledger.minor_digits} 位小數。`,
      };
    await tripRequest(`/trips/${tripId}/settlements`, {
      method: "POST",
      body: JSON.stringify({
        sender_id: Number(values.sender_id),
        recipient_id: Number(values.recipient_id),
        amount_minor: amount,
        settled_on: values.settled_on,
        notes: values.notes || null,
      }),
    });
  } catch (error) {
    return { values, error: errorMessage(error) };
  }
  revalidatePath(`/trips/${tripId}/expenses`);
  redirect(`/trips/${tripId}/expenses`);
}
export async function deleteLedgerEntry(
  tripId: number,
  kind: "expenses" | "settlements",
  id: number,
): Promise<MutationState> {
  if (
    !isTripId(tripId) ||
    !isTripId(id) ||
    !["expenses", "settlements"].includes(kind)
  )
    return { error: "找不到紀錄。" };
  try {
    await tripRequest(`/trips/${tripId}/${kind}/${id}`, { method: "DELETE" });
  } catch (error) {
    return { error: errorMessage(error) };
  }
  revalidatePath(`/trips/${tripId}/expenses`);
  return {
    success: kind === "settlements" ? "已撤銷還款紀錄。" : "已刪除費用。",
  };
}
