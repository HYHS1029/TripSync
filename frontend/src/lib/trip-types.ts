export type Trip = {
  id: number;
  name: string;
  destination: string;
  start_date: string;
  end_date: string;
  description: string | null;
  owner_id: number;
  created_at: string;
  updated_at: string;
};

export type TripValues = {
  name: string;
  destination: string;
  start_date: string;
  end_date: string;
  description: string;
};

export type TripFormState = {
  values: TripValues;
  error?: string;
  fieldErrors?: Partial<Record<keyof TripValues, string>>;
};

export type DeleteTripState = { error?: string };

export type MutationState = { error?: string; success?: string };
export type TripMember = {
  user_id: number;
  username: string;
  joined_at: string;
  is_owner: boolean;
};
export type Invitation = {
  id: number;
  created_at: string;
  expires_at: string;
  revoked_at: string | null;
  accepted_at: string | null;
  status: "revoked" | "used" | "expired" | "pending";
};
export type InvitationState = MutationState & { invitePath?: string };
export type ActivityValues = {
  title: string;
  activity_date: string;
  start_time: string;
  end_time: string;
  location: string;
  notes: string;
};
export type Activity = Omit<
  ActivityValues,
  "start_time" | "end_time" | "location" | "notes"
> & {
  id: number;
  trip_id: number;
  created_by: number;
  start_time: string | null;
  end_time: string | null;
  location: string | null;
  notes: string | null;
};
export type ActivityFormState = {
  values: ActivityValues;
  error?: string;
  fieldErrors?: Partial<Record<keyof ActivityValues, string>>;
};

export function tripDays(trip: Trip): number {
  return (
    Math.round(
      (Date.parse(trip.end_date) - Date.parse(trip.start_date)) / 86_400_000,
    ) + 1
  );
}

export function addDays(day: string, amount: number): string {
  const date = new Date(`${day}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}

export function isTripDay(day: unknown, trip: Trip): day is string {
  return Boolean(
    typeof day === "string" &&
      /^\d{4}-\d{2}-\d{2}$/.test(day) &&
      day >= trip.start_date &&
      day <= trip.end_date &&
      Number.isFinite(Date.parse(day)) &&
      new Date(day).toISOString().slice(0, 10) === day,
  );
}

export function formatTripDate(value: string): string {
  return new Intl.DateTimeFormat("zh-TW", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}
