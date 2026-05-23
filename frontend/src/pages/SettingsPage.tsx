import { Box } from "@mui/material";
import { useCallback, useEffect, useRef, useState } from "react";

import AppShell from "../components/layout/AppShell";
import NotificationRow, {
  type SaveState,
} from "../components/settings/NotificationRow";
import SettingsSection from "../components/settings/SettingsSection";
import { useAuth } from "../hooks/useAuth";
import {
  updateEmailNotifications,
  updateSmsNotifications,
} from "../services/accountsService";
import { semantic } from "../theme/tokens";
import type { NotificationSettings } from "../types/user";
import {
  getUserFriendlyMessage,
  toApiError,
} from "../utils/errorMessages";

type Channel = "email" | "sms";

const SUCCESS_DISPLAY_MS = 1500;

export default function SettingsPage() {
  const { user, updateNotificationSettings } = useAuth();

  const [emailSaveState, setEmailSaveState] = useState<SaveState>("idle");
  const [smsSaveState, setSmsSaveState] = useState<SaveState>("idle");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [smsError, setSmsError] = useState<string | null>(null);

  const timersRef = useRef<{ email: number | null; sms: number | null }>({
    email: null,
    sms: null,
  });
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (timersRef.current.email !== null) {
        window.clearTimeout(timersRef.current.email);
      }
      if (timersRef.current.sms !== null) {
        window.clearTimeout(timersRef.current.sms);
      }
    };
  }, []);

  const scheduleIdle = (channel: Channel) => {
    if (timersRef.current[channel] !== null) {
      window.clearTimeout(timersRef.current[channel]!);
    }
    timersRef.current[channel] = window.setTimeout(() => {
      if (!mountedRef.current) return;
      if (channel === "email") setEmailSaveState("idle");
      else setSmsSaveState("idle");
      timersRef.current[channel] = null;
    }, SUCCESS_DISPLAY_MS);
  };

  const handleToggle = useCallback(
    async (channel: Channel, newValue: boolean) => {
      if (!user) return;
      const previousSettings: NotificationSettings = user.settings;
      const optimisticSettings: NotificationSettings = {
        ...previousSettings,
        ...(channel === "email"
          ? { allow_email: newValue }
          : { allow_sms: newValue }),
      };

      updateNotificationSettings(optimisticSettings);
      if (channel === "email") {
        setEmailSaveState("saving");
        setEmailError(null);
      } else {
        setSmsSaveState("saving");
        setSmsError(null);
      }

      try {
        const response = await (channel === "email"
          ? updateEmailNotifications(newValue)
          : updateSmsNotifications(newValue));
        if (!mountedRef.current) return;
        updateNotificationSettings(response.data.settings);
        if (channel === "email") setEmailSaveState("success");
        else setSmsSaveState("success");
        scheduleIdle(channel);
      } catch (err) {
        if (!mountedRef.current) return;
        updateNotificationSettings(previousSettings);
        const apiError = toApiError(err);
        const message = getUserFriendlyMessage(apiError);
        if (channel === "email") {
          setEmailSaveState("error");
          setEmailError(message);
        } else {
          setSmsSaveState("error");
          setSmsError(message);
        }
      }
    },
    [user, updateNotificationSettings],
  );

  if (!user) {
    return <AppShell><Box /></AppShell>;
  }

  return (
    <AppShell>
      <Box component="section" sx={{ marginBottom: "48px" }}>
        <Box
          component="h1"
          sx={{
            fontSize: 24,
            fontWeight: 600,
            letterSpacing: "-0.02em",
            color: semantic.textPrimary,
            margin: 0,
            lineHeight: 1.25,
          }}
        >
          Ajustes
        </Box>
        <Box
          sx={{
            marginTop: "4px",
            fontSize: 14,
            color: semantic.textSecondary,
            lineHeight: 1.5,
          }}
        >
          Gestiona tus preferencias de cuenta y notificaciones.
        </Box>
      </Box>

      <SettingsSection
        title="Notificaciones"
        description="Elige cómo quieres recibir avisos cuando ocurra actividad en tu cuenta, como una suscripción exitosa o cancelación."
      >
        <NotificationRow
          label="Notificaciones por email"
          secondaryText={user.email}
          checked={user.settings.allow_email}
          onChange={(next) => handleToggle("email", next)}
          saveState={emailSaveState}
          errorMessage={emailError}
        />
        <NotificationRow
          label="Notificaciones por SMS"
          secondaryText={user.telefono}
          checked={user.settings.allow_sms}
          onChange={(next) => handleToggle("sms", next)}
          saveState={smsSaveState}
          errorMessage={smsError}
          isLast
        />
      </SettingsSection>

      <Box
        component="aside"
        sx={{
          marginTop: "32px",
          padding: "20px",
          backgroundColor: semantic.backgroundSubtle,
          border: `1px solid ${semantic.borderSubtle}`,
          borderRadius: "6px",
        }}
      >
        <Box
          sx={{
            fontSize: 13,
            fontWeight: 500,
            color: semantic.textPrimary,
            lineHeight: 1.4,
            marginBottom: "8px",
          }}
        >
          Sobre las notificaciones
        </Box>
        <Box
          component="ul"
          sx={{
            margin: 0,
            paddingInlineStart: "20px",
            fontSize: 13,
            color: semantic.textSecondary,
            lineHeight: 1.6,
            display: "flex",
            flexDirection: "column",
            gap: "2px",
          }}
        >
          <li>Confirmación de suscripción a un fondo.</li>
          <li>Confirmación de cancelación de suscripción.</li>
        </Box>
        <Box
          sx={{
            marginTop: "12px",
            fontSize: 12,
            fontStyle: "italic",
            color: semantic.textTertiary,
            lineHeight: 1.5,
          }}
        >
          Solo se envían notificaciones por los canales habilitados arriba.
          Puedes cambiar tus preferencias en cualquier momento.
        </Box>
      </Box>
    </AppShell>
  );
}
