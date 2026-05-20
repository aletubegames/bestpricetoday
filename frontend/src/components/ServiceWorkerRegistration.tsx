"use client";

import { useEffect } from "react";

export default function ServiceWorkerRegistration() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    const clearServiceWorker = async () => {
      try {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.map((registration) => registration.unregister()));

        if ("caches" in window) {
          const cacheKeys = await caches.keys();
          await Promise.all(cacheKeys.filter((key) => key.startsWith("bpt-")).map((key) => caches.delete(key)));
        }

        const shouldReloadAdmin = window.location.pathname.startsWith("/admin")
          && registrations.length > 0
          && !sessionStorage.getItem("bpt_sw_cleanup_reloaded");
        if (shouldReloadAdmin) {
          sessionStorage.setItem("bpt_sw_cleanup_reloaded", "1");
          window.location.reload();
        }
      } catch (error: unknown) {
        console.warn("Service worker cleanup failed:", error);
      }
    };

    clearServiceWorker();
  }, []);

  return null;
}