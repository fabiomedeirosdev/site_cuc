let installationPrompt = null;
let registrationPromise = null;
const deviceKey = "rhema-push-device";

export function isInstalled() {
  return Boolean(globalThis.matchMedia?.("(display-mode: standalone)").matches || globalThis.navigator?.standalone);
}

export function supportsPush() {
  return Boolean(globalThis.isSecureContext && "serviceWorker" in navigator && "PushManager" in globalThis && "Notification" in globalThis);
}

export function registerPwa() {
  if (!("serviceWorker" in navigator) || !globalThis.isSecureContext) return Promise.resolve(null);
  registrationPromise ??= navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(() => {
    registrationPromise = null;
    return null;
  });
  return registrationPromise;
}

export function initializePwa() {
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    installationPrompt = event;
    window.dispatchEvent(new Event("rhema-install-change"));
  });
  window.addEventListener("appinstalled", () => {
    installationPrompt = null;
    window.dispatchEvent(new Event("rhema-app-installed"));
  });
  registerPwa();
}

export async function promptInstallation() {
  if (!installationPrompt) return false;
  const prompt = installationPrompt;
  installationPrompt = null;
  await prompt.prompt();
  return (await prompt.userChoice).outcome === "accepted";
}

export function applicationServerKey(value) {
  const raw = atob(value.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - value.length % 4) % 4));
  return Uint8Array.from(raw, (character) => character.charCodeAt(0));
}

function deviceToken(create = false) {
  let token = localStorage.getItem(deviceKey);
  if (!token && create) {
    const bytes = crypto.getRandomValues(new Uint8Array(32));
    token = btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    localStorage.setItem(deviceKey, token);
  }
  return token;
}

function subscriptionData(subscription, token) {
  const data = subscription.toJSON();
  return { endpoint: data.endpoint, p256dh: data.keys.p256dh, auth: data.keys.auth, device_token: token };
}

export async function currentPushSubscription() {
  if (!supportsPush()) return null;
  const registration = await registerPwa();
  return registration ? registration.pushManager.getSubscription() : null;
}

export async function syncPushSubscription(api) {
  if (!supportsPush() || Notification.permission !== "granted") return;
  const subscription = await currentPushSubscription();
  const token = deviceToken();
  if (subscription && token) await api.savePushSubscription(subscriptionData(subscription, token));
}

export async function enableNotifications(api) {
  if (!supportsPush()) throw new Error("Este navegador não oferece notificações. Abra o app instalado em um navegador compatível.");
  // Call permission directly from the user's click, before any network await.
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("As notificações não foram autorizadas. Você pode alterar a permissão nas configurações do navegador.");
  const config = await api.getPushConfig();
  if (!config.enabled) throw new Error("As notificações ainda não estão disponíveis. Tente novamente mais tarde.");
  const registration = await registerPwa();
  if (!registration) throw new Error("Não foi possível preparar o aplicativo. Recarregue a página e tente novamente.");
  // Registration may still be installing on the first visit.
  await navigator.serviceWorker.ready;
  let subscription = await registration.pushManager.getSubscription();
  if (subscription && !deviceToken()) {
    await subscription.unsubscribe();
    subscription = null;
  }
  const token = deviceToken(true);
  subscription ??= await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: applicationServerKey(config.public_key) });
  try {
    await api.savePushSubscription(subscriptionData(subscription, token));
  } catch (error) {
    // Do not leave an unregistered browser subscription presented as enabled.
    await subscription.unsubscribe();
    throw error;
  }
  return subscription;
}

export async function disableNotifications(api) {
  const subscription = await currentPushSubscription();
  if (!subscription) return;
  const token = deviceToken();
  let serverError;
  try {
    if (token) await api.deletePushSubscription({ endpoint: subscription.endpoint, device_token: token });
  } catch (error) { serverError = error; }
  // Provider cancellation still stops delivery when the API is unavailable.
  const removed = await subscription.unsubscribe();
  if (!removed && serverError) throw serverError;
}

export async function clearPushNotifications() {
  const registration = await registerPwa();
  if (registration) for (const notification of await registration.getNotifications()) notification.close();
}
