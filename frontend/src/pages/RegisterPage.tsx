import { Box } from "@mui/material";
import { motion } from "framer-motion";
import {
  useRef,
  useState,
  type FocusEvent,
  type FormEvent,
} from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";

import Button from "../components/Button";
import ErrorAlert from "../components/ErrorAlert";
import { CheckIcon } from "../components/icons";
import Input from "../components/Input";
import Wordmark from "../components/Wordmark";
import { useAuth } from "../hooks/useAuth";
import { register as registerRequest } from "../services/authService";
import { colors, semantic } from "../theme/tokens";
import type { ApiError } from "../types/common";
import { toApiError } from "../utils/errorMessages";
import {
  isValidEmail,
  isValidPhoneE164,
  validateName,
  validatePasswordStrength,
} from "../utils/validators";

interface FormState {
  nombre: string;
  apellido: string;
  email: string;
  telefono: string;
  password: string;
}

type FieldKey = keyof FormState;
type FieldErrors = Partial<Record<FieldKey, string>>;

const initial: FormState = {
  nombre: "",
  apellido: "",
  email: "",
  telefono: "",
  password: "",
};

function validate(values: FormState): FieldErrors {
  const errors: FieldErrors = {};
  const nombreErr = validateName(values.nombre, "nombre");
  if (nombreErr) errors.nombre = nombreErr;
  const apellidoErr = validateName(values.apellido, "apellido");
  if (apellidoErr) errors.apellido = apellidoErr;
  if (!isValidEmail(values.email)) errors.email = "Ingresa un correo válido";
  if (!isValidPhoneE164(values.telefono)) {
    errors.telefono = "Formato inválido. Debe empezar con +";
  }
  const pw = validatePasswordStrength(values.password);
  if (!pw.valid) errors.password = pw.errors[0] ?? "Contraseña inválida";
  return errors;
}

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const refs: Record<FieldKey, React.RefObject<HTMLInputElement | null>> = {
    nombre: useRef<HTMLInputElement>(null),
    apellido: useRef<HTMLInputElement>(null),
    email: useRef<HTMLInputElement>(null),
    telefono: useRef<HTMLInputElement>(null),
    password: useRef<HTMLInputElement>(null),
  };

  const [values, setValues] = useState<FormState>(initial);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);

  const pwCriteria = validatePasswordStrength(values.password).criteria;
  const showPwCriteria = values.password.length > 0;

  const setField = <K extends FieldKey>(key: K, value: FormState[K]) => {
    setValues((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
    if (submitError) setSubmitError(null);
  };

  const handleBlur =
    (key: FieldKey) =>
    (_: FocusEvent<HTMLInputElement>): void => {
      const result = validate(values);
      setErrors((prev) => ({ ...prev, [key]: result[key] }));
    };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (loading) return;
    const next = validate(values);
    setErrors(next);
    const firstErrorKey = (Object.keys(next) as FieldKey[]).find(
      (k) => next[k],
    );
    if (firstErrorKey) {
      refs[firstErrorKey].current?.focus();
      return;
    }

    setLoading(true);
    setSubmitError(null);
    try {
      const response = await registerRequest({
        nombre: values.nombre.trim(),
        apellido: values.apellido.trim(),
        email: values.email.trim(),
        telefono: values.telefono.trim(),
        password: values.password,
      });
      await register(response.data.access_token, response.data.user);
      navigate("/", { replace: true });
    } catch (err) {
      const apiError = toApiError(err);
      setSubmitError(apiError);
      const errorCode = apiError.error;
      if (errorCode === "EMAIL_ALREADY_EXISTS") {
        refs.email.current?.focus();
      } else if (errorCode === "PHONE_ALREADY_EXISTS") {
        refs.telefono.current?.focus();
      } else {
        refs.nombre.current?.focus();
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        backgroundColor: semantic.background,
        position: "relative",
      }}
    >
      <Wordmark />
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: { xs: "96px 24px 48px", sm: "120px 24px 48px" },
        }}
      >
        <Box
          component={motion.div}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
          sx={{ width: "100%", maxWidth: 360 }}
        >
          <Box
            component="h1"
            sx={{
              fontSize: 32,
              lineHeight: 1.15,
              fontWeight: 600,
              letterSpacing: "-0.025em",
              color: semantic.textPrimary,
              margin: 0,
              marginBottom: "8px",
            }}
          >
            Crear cuenta
          </Box>
          <Box
            sx={{
              fontSize: 14,
              lineHeight: 1.5,
              color: semantic.textSecondary,
              marginBottom: "40px",
            }}
          >
            Comienza a invertir en fondos de inversión.
          </Box>

          <Box
            component="form"
            onSubmit={handleSubmit}
            noValidate
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: "20px",
            }}
          >
            <Box
              sx={{
                display: "grid",
                gap: "16px",
                gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
              }}
            >
              <Input
                ref={refs.nombre}
                label="Nombre"
                placeholder="Mateo"
                autoComplete="given-name"
                value={values.nombre}
                onChange={(e) => setField("nombre", e.target.value)}
                onBlur={handleBlur("nombre")}
                error={!!errors.nombre}
                errorMessage={errors.nombre}
                disabled={loading}
              />
              <Input
                ref={refs.apellido}
                label="Apellido"
                placeholder="Jiménez"
                autoComplete="family-name"
                value={values.apellido}
                onChange={(e) => setField("apellido", e.target.value)}
                onBlur={handleBlur("apellido")}
                error={!!errors.apellido}
                errorMessage={errors.apellido}
                disabled={loading}
              />
            </Box>

            <Input
              ref={refs.email}
              label="Correo electrónico"
              type="email"
              placeholder="tu@correo.com"
              autoComplete="email"
              value={values.email}
              onChange={(e) => setField("email", e.target.value)}
              onBlur={handleBlur("email")}
              error={!!errors.email}
              errorMessage={errors.email}
              disabled={loading}
            />

            <Input
              ref={refs.telefono}
              label="Teléfono"
              type="tel"
              placeholder="+573001234567"
              autoComplete="tel"
              value={values.telefono}
              onChange={(e) => setField("telefono", e.target.value)}
              onBlur={handleBlur("telefono")}
              error={!!errors.telefono}
              errorMessage={errors.telefono}
              helperText={
                errors.telefono ? undefined : "Formato internacional, p. ej. +573001234567"
              }
              disabled={loading}
            />

            <Box>
              <Input
                ref={refs.password}
                label="Contraseña"
                type="password"
                placeholder="••••••••"
                autoComplete="new-password"
                value={values.password}
                onChange={(e) => setField("password", e.target.value)}
                onBlur={handleBlur("password")}
                error={!!errors.password}
                errorMessage={errors.password}
                helperText={
                  errors.password || showPwCriteria
                    ? undefined
                    : "Mínimo 8 caracteres, una mayúscula y un número."
                }
                disabled={loading}
              />
              {showPwCriteria && !errors.password ? (
                <Box
                  sx={{
                    marginTop: "8px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "4px",
                  }}
                >
                  {pwCriteria.map((c) => (
                    <Box
                      key={c.label}
                      sx={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        fontSize: 12,
                        color: c.met
                          ? semantic.textPrimary
                          : semantic.textTertiary,
                      }}
                    >
                      <Box
                        sx={{
                          display: "inline-flex",
                          width: 14,
                          height: 14,
                          color: c.met ? semantic.textPrimary : colors.gray300,
                        }}
                      >
                        <CheckIcon size={14} />
                      </Box>
                      <Box
                        sx={{
                          textDecoration: c.met ? "line-through" : "none",
                          textDecorationColor: semantic.textTertiary,
                        }}
                      >
                        {c.label}
                      </Box>
                    </Box>
                  ))}
                </Box>
              ) : null}
            </Box>

            <Box sx={{ marginTop: "4px" }}>
              <ErrorAlert error={submitError}>
                {submitError?.error === "EMAIL_ALREADY_EXISTS" ? (
                  <>
                    Este correo ya está registrado.{" "}
                    <Box
                      component={RouterLink}
                      to="/login"
                      sx={{
                        color: "inherit",
                        fontWeight: 500,
                        textDecoration: "underline",
                        textUnderlineOffset: "3px",
                      }}
                    >
                      Inicia sesión
                    </Box>
                    .
                  </>
                ) : undefined}
              </ErrorAlert>
            </Box>

            <Box sx={{ marginTop: "8px" }}>
              <Button type="submit" variant="primary" fullWidth loading={loading}>
                Crear cuenta
              </Button>
            </Box>
          </Box>

          <Box
            sx={{
              marginTop: "32px",
              textAlign: "center",
              fontSize: 13,
              color: semantic.textSecondary,
            }}
          >
            ¿Ya tienes cuenta?{" "}
            <Box
              component={RouterLink}
              to="/login"
              sx={{
                color: semantic.textPrimary,
                fontWeight: 500,
                textDecoration: "underline",
                textUnderlineOffset: "3px",
                textDecorationColor: "#D4D4D4",
                transition: "text-decoration-color 150ms ease",
                "&:hover": { textDecorationColor: semantic.textPrimary },
              }}
            >
              Iniciar sesión
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
