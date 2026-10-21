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

export function formatTripDate(value: string): string {
  return new Intl.DateTimeFormat("zh-TW", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}
