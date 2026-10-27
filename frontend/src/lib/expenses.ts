import "server-only";
import { handlePageError, tripRequest } from "./trips";
import type { Ledger } from "./expense-types";

export async function getLedger(tripId: string): Promise<Ledger> {
  try {
    return await tripRequest<Ledger>(`/trips/${tripId}/ledger`);
  } catch (error) {
    handlePageError(error);
  }
}
