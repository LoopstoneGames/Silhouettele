/**
 * Lightweight error logger. Logs to the console only outside production builds
 * so internal details aren't surfaced in the production bundle. Swap the dev
 * branch for a real reporting service (Sentry/LogRocket) later if needed.
 */
export const logError = (...args) => {
  if (process.env.NODE_ENV !== "production") {
    // eslint-disable-next-line no-console
    console.error(...args);
  }
};
