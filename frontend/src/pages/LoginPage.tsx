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
import Input from "../components/Input";
import Wordmark from "../components/Wordmark";
import { useAuth } from "../hooks/useAuth";
import { login as loginRequest } from "../services/authService";
import { semantic } from "../theme/tokens";
import type { ApiError } from "../types/common";
import { toApiError } from "../utils/errorMessages";
import { isValidEmail } from "../utils/validators";

interface FormState {
  email: string;
  password: string;
}

type FieldErrors = Partial<Record<keyof FormState, string>>;

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  const [values, setValues] = useState<FormState>({ email: "", password: "" });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);

  const setField = <K extends keyof FormState>(
    key: K,
    value: FormState[K],
  ) => {
    setValues((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
    if (submitError) setSubmitError(null);
  };

  const validateField = (key: keyof FormState, value: string): string | undefined => {
    if (key === "email") {
      if (!value.trim()) return "Ingresa un correo válido";
      if (!isValidEmail(value)) return "Ingresa un correo válido";
    }
    if (key === "password") {
      if (!value) return "Ingresa tu contraseña";
    }
    return undefined;
  };

  const handleBlur =
    (key: keyof FormState) =>
    (e: FocusEvent<HTMLInputElement>): void => {
      const err = validateField(key, e.target.value);
      setErrors((prev) => ({ ...prev, [key]: err }));
    };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (loading) return;
    const next: FieldErrors = {
      email: validateField("email", values.email),
      password: validateField("password", values.password),
    };
    setErrors(next);
    if (next.email || next.password) {
      if (next.email) emailRef.current?.focus();
      else if (next.password) passwordRef.current?.focus();
      return;
    }

    setLoading(true);
    setSubmitError(null);
    try {
      const response = await loginRequest({
        email: values.email.trim(),
        password: values.password,
      });
      await login(response.data.access_token);
      navigate("/", { replace: true });
    } catch (err) {
      const apiError = toApiError(err);
      setSubmitError(apiError);
      emailRef.current?.focus();
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
            Iniciar sesión
          </Box>
          <Box
            sx={{
              fontSize: 14,
              lineHeight: 1.5,
              color: semantic.textSecondary,
              marginBottom: "40px",
            }}
          >
            Bienvenido de vuelta.
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
            <Input
              ref={emailRef}
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
              ref={passwordRef}
              label="Contraseña"
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
              value={values.password}
              onChange={(e) => setField("password", e.target.value)}
              onBlur={handleBlur("password")}
              error={!!errors.password}
              errorMessage={errors.password}
              disabled={loading}
            />

            <Box sx={{ marginTop: "4px" }}>
              <ErrorAlert error={submitError} />
            </Box>

            <Box sx={{ marginTop: "8px" }}>
              <Button type="submit" variant="primary" fullWidth loading={loading}>
                Continuar
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
            ¿No tienes cuenta?{" "}
            <Box
              component={RouterLink}
              to="/register"
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
              Crear una
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
