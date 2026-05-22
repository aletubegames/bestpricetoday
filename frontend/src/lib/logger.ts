/**
 * Centralized error/warning logger for frontend
 * Wraps console methods with environment checks
 */

const isDev = process.env.NODE_ENV === 'development';

export const logger = {
  error: (message: string, error?: any) => {
    if (isDev) {
      console.error(`[ERROR] ${message}`, error);
    }
    // TODO: Send to error tracking service (Sentry, etc.) in production
  },

  warn: (message: string, data?: any) => {
    if (isDev) {
      console.warn(`[WARN] ${message}`, data);
    }
  },

  debug: (message: string, data?: any) => {
    if (isDev) {
      console.debug(`[DEBUG] ${message}`, data);
    }
  },

  info: (message: string, data?: any) => {
    if (isDev) {
      console.info(`[INFO] ${message}`, data);
    }
  },
};
