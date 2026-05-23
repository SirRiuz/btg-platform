import type { Transaction } from "../types/transaction";

export interface TransactionGroup {
  dateKey: string;
  label: string;
  items: Transaction[];
}

const TZ_INFO_REGEX = /(Z|[+-]\d{2}:?\d{2})$/;

/**
 * Parse a backend ISO 8601 timestamp into a Date.
 *
 * The backend currently serializes naive datetimes — strings like
 * "2026-05-22T21:17:00" without a Z or offset. JS would interpret those as
 * LOCAL time, shifting the instant by the client's offset. We defend
 * against that by appending "Z" when no timezone marker is present.
 * The backend's stored datetime is UTC by construction
 * (`datetime.now(timezone.utc)`), so treating naive strings as UTC is
 * correct.
 */
export function parseTimestamp(isoOrDate: string | Date): Date {
  if (isoOrDate instanceof Date) return isoOrDate;
  const hasTz = TZ_INFO_REGEX.test(isoOrDate);
  return new Date(hasTz ? isoOrDate : `${isoOrDate}Z`);
}

const dateLabelFormatter = new Intl.DateTimeFormat("es-CO", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

const longDateFormatter = new Intl.DateTimeFormat("es-CO", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

const timeFormatter = new Intl.DateTimeFormat("es-CO", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const fullDateTimeFormatter = new Intl.DateTimeFormat("es-CO", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function stripTrailingPeriod(value: string): string {
  return value.replace(/\.(?=\s|,|$)/g, "");
}

/**
 * "YYYY-MM-DD" in the user's LOCAL calendar (not UTC). Used as a stable
 * key for grouping transactions by day. Lexicographic order matches
 * chronological order, so it can be sorted as a string.
 */
export function getLocalDateKey(date: Date): string {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export function isSameLocalDay(a: Date, b: Date): boolean {
  return getLocalDateKey(a) === getLocalDateKey(b);
}

/** "Hoy" / "Ayer" / "22 may 2026" — always in local calendar. */
export function formatDateLabel(date: Date, now: Date = new Date()): string {
  if (isSameLocalDay(date, now)) return "Hoy";
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  if (isSameLocalDay(date, yesterday)) return "Ayer";
  return stripTrailingPeriod(dateLabelFormatter.format(date));
}

/** "23:42" in local time. */
export function formatTimeLabel(date: Date): string {
  return timeFormatter.format(date);
}

/** "22 may 2026, 23:42" in local time. */
export function formatFullDateTime(date: Date): string {
  return stripTrailingPeriod(fullDateTimeFormatter.format(date));
}

/** "22 de mayo de 2026" — long-form local date, accepts an ISO string. */
export function formatRelativeDate(isoOrDate: string | Date): string {
  const date = parseTimestamp(isoOrDate);
  return longDateFormatter.format(date);
}

/**
 * Group transactions by local calendar day, with groups sorted DESC by
 * day and items within each group sorted DESC by timestamp.
 */
export function groupTransactionsByDate(
  transactions: Transaction[],
  now: Date = new Date(),
): TransactionGroup[] {
  const map = new Map<string, Transaction[]>();
  for (const tx of transactions) {
    const date = parseTimestamp(tx.timestamp);
    const key = getLocalDateKey(date);
    const bucket = map.get(key);
    if (bucket) bucket.push(tx);
    else map.set(key, [tx]);
  }

  const groups: TransactionGroup[] = Array.from(map.entries()).map(
    ([dateKey, items]) => {
      const sortedItems = [...items].sort(
        (a, b) =>
          parseTimestamp(b.timestamp).getTime() -
          parseTimestamp(a.timestamp).getTime(),
      );
      const sample = parseTimestamp(sortedItems[0].timestamp);
      return {
        dateKey,
        label: formatDateLabel(sample, now),
        items: sortedItems,
      };
    },
  );

  groups.sort((a, b) => b.dateKey.localeCompare(a.dateKey));
  return groups;
}
