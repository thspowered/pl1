import { useState } from 'react';

type NotificationSeverity = 'success' | 'error' | 'info' | 'warning';

interface Notification {
  open: boolean;
  message: string;
  severity: NotificationSeverity;
}

export const useNotification = () => {
  const [notification, setNotification] = useState<Notification>({
    open: false,
    message: '',
    severity: 'info',
  });

  const showNotification = (message: string, severity: NotificationSeverity = 'info') => {
    setNotification({
      open: true,
      message,
      severity,
    });
  };

  const closeNotification = () => {
    setNotification(prev => ({ ...prev, open: false }));
  };

  const showSuccess = (message: string) => showNotification(message, 'success');
  const showError = (message: string) => showNotification(message, 'error');
  const showInfo = (message: string) => showNotification(message, 'info');
  const showWarning = (message: string) => showNotification(message, 'warning');

  return {
    notification,
    showNotification,
    closeNotification,
    showSuccess,
    showError,
    showInfo,
    showWarning
  };
}; 