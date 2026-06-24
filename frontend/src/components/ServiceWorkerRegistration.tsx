"use client";

import { useEffect } from "react";

export default function ServiceWorkerRegistration() {
  useEffect(() => {
    // Completely disable service worker for CORS debugging
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.getRegistrations().then((registrations) => {
        registrations.forEach((registration) => {
          registration.unregister();
        });
      });
    }

    // Clear all caches
    if ("caches" in window) {
      caches.keys().then((cacheKeys) => {
        cacheKeys.forEach((key) => {
          caches.delete(key);
        });
      });
    }
  }, []);

  return null;
}