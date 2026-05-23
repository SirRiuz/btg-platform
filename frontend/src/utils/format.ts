const copFormatter = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export function formatCOP(amount: number): string {
  if (!Number.isFinite(amount)) return "—";
  return copFormatter.format(Math.round(amount));
}

export function parseAmountInput(raw: string): number | null {
  const digits = raw.replace(/[^0-9]/g, "");
  if (digits.length === 0) return null;
  const normalized = digits.replace(/^0+(?=\d)/, "");
  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
}
