export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const PHONE_E164_REGEX = /^\+[1-9]\d{1,14}$/;
export const NAME_REGEX = /^[A-Za-zÁÉÍÓÚÑáéíóúñ\s'-]+$/;

export function isValidEmail(value: string): boolean {
  return EMAIL_REGEX.test(value.trim());
}

export function isValidPhoneE164(value: string): boolean {
  return PHONE_E164_REGEX.test(value.trim());
}

export interface PasswordStrengthResult {
  valid: boolean;
  errors: string[];
  criteria: Array<{ label: string; met: boolean }>;
}

export function validatePasswordStrength(
  password: string,
): PasswordStrengthResult {
  const criteria = [
    { label: "Mínimo 8 caracteres", met: password.length >= 8 },
    { label: "Una mayúscula", met: /[A-Z]/.test(password) },
    { label: "Una minúscula", met: /[a-z]/.test(password) },
    { label: "Un número", met: /\d/.test(password) },
  ];
  const errors = criteria.filter((c) => !c.met).map((c) => `Debe incluir: ${c.label.toLowerCase()}`);
  return {
    valid: errors.length === 0,
    errors,
    criteria,
  };
}

export function validateName(
  value: string,
  field: string,
): string | null {
  const trimmed = value.trim();
  if (!trimmed) return `${capitalize(field)} es obligatorio.`;
  if (trimmed.length < 2 || trimmed.length > 50) {
    return "Solo letras, mínimo 2 caracteres.";
  }
  if (!NAME_REGEX.test(trimmed)) {
    return "Solo letras, mínimo 2 caracteres.";
  }
  return null;
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
