export class ApiError extends Error {
  constructor(status, data) {
    const messages = (value) => typeof value === "string" ? [value] : value && typeof value === "object" ? Object.values(value).flatMap(messages) : [];
    super(messages(data).join(" ") || `A API respondeu com status ${status}.`);
    this.status = status;
  }
}

export function createApiClient({ baseUrl = "", fetchImpl = globalThis.fetch } = {}) {
  const base = baseUrl.replace(/\/+$/, "");
  let pendingCsrf = null;

  async function request(path, { signal, method = "GET", body, csrfToken } = {}) {
    const multipart = typeof FormData !== "undefined" && body instanceof FormData;
    const response = await fetchImpl(`${base}${path}`, {
      method,
      headers: {
        Accept: "application/json",
        ...(body !== undefined && !multipart ? { "Content-Type": "application/json" } : {}),
        ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      },
      credentials: "include",
      cache: "no-store",
      signal: signal ?? AbortSignal.timeout(10000),
      ...(body !== undefined ? { body: multipart ? body : JSON.stringify(body) } : {}),
    });
    let data;
    try { data = await response.json(); } catch { data = null; }
    if (!response.ok) {
      throw new ApiError(response.status, data);
    }
    return data;
  }

  async function write(path, method, body, options = {}) {
    // Obtain a fresh masked token, including after login/logout token rotation.
    // Concurrent first writes must share the same cookie/token pair. Otherwise
    // two anonymous CSRF responses can replace each other's cookies.
    if (!pendingCsrf) {
      pendingCsrf = request("/api/auth/csrf", options).finally(() => { pendingCsrf = null; });
    }
    const csrf = await pendingCsrf;
    return request(path, { ...options, method, body, csrfToken: csrf.csrf_token });
  }

  return {
    getNotifications: (options) => request("/api/notifications", options),
    readNotifications: (seen_until) => write("/api/notifications", "POST", { seen_until }),
    getInbox: (page = 1, status = "pending", options) => request(`/api/inbox?page=${page}&status=${status}`, options),
    getIncomingMessage: (id, options) => request(`/api/inbox/${id}`, options),
    respondToIncomingMessage: (id, responded) => write(`/api/inbox/${id}`, "PATCH", { responded }),
    getTeam: (page = 1, query = "", options) => request(`/api/management/team?page=${page}&q=${encodeURIComponent(query)}`, options),
    addTeamMember: (data) => write("/api/management/team", "POST", data),
    updateTeamMember: (id, data) => write(`/api/management/team/${id}`, "PATCH", data),
    getGroupArticles: (slug, page = 1, options) => request(`/api/articles?group=${encodeURIComponent(slug)}&page=${page}`, options),
    getEvents: (page = 1, past = false, options) => request(`/api/events?page=${page}&past=${past ? 1 : 0}`, options),
    getMural: (page = 1, options) => request(`/api/mural?page=${page}`, options),
    getCommunications: (kind, page = 1, options) => request(`/api/communications/${kind}?page=${page}`, options),
    saveCommunication: (kind, id, data) => write(`/api/communications/${kind}${id ? `/${id}` : ""}`, id ? "PATCH" : "POST", data),
    deleteCommunication: (kind, id) => write(`/api/communications/${kind}/${id}`, "DELETE"),
    getCommunicationDelegation: (options) => request("/api/communications/delegation", options),
    setCommunicationDelegate: (data) => write("/api/communications/delegation", "PUT", data),
    getWeeklyNewsletter: (options) => request("/api/communications/weekly", options),
    saveWeeklyNewsletter: (data) => write("/api/communications/weekly", "PUT", data),
    previewNewsletter: (data) => write("/api/communications/preview", "POST", data),
    getNewsletterPreference: (options) => request("/api/newsletter/preference", options),
    saveNewsletterPreference: (opted_in) => write("/api/newsletter/preference", "PUT", { opted_in }),
    requestNewsletter: (email, accepted) => write("/api/newsletter/request", "POST", { email, accepted }),
    newsletterAction: (action, token) => write("/api/newsletter/action", "POST", { action, token }),
    getBillingConfig: (options) => request("/api/billing/config", options),
    createCheckout: (data, options) => write("/api/billing/checkout", "POST", data, options),
    checkInvitation: (token, options) => write("/api/billing/invitation/check", "POST", { token }, options),
    completeInvitation: (data, options) => write("/api/billing/invitation/complete", "POST", data, options),
    resendInvitation: (email, options) => write("/api/billing/invitation/resend", "POST", { email }, options),
    getSubscriptions: (options) => request("/api/billing/mine", options),
    cancelSubscription: (id, options) => write(`/api/billing/subscriptions/${id}/cancel`, "POST", {}, options),
    createConsumerRequest: (id, data, options) => write(`/api/billing/subscriptions/${id}/requests`, "POST", data, options),
    getArticles: (page = 1, query = "", options) => request(`/api/articles?page=${page}&q=${encodeURIComponent(query)}`, options),
    getArticle: (id, options) => request(`/api/articles/${id}`, options),
    getEditorArticles: (page = 1, options) => request(`/api/editorial/articles?page=${page}`, options),
    getEditorArticle: (id, options) => request(`/api/editorial/articles/${id}`, options),
    getAuthorGroups: (options) => request("/api/editorial/author-groups", options),
    createArticle: (data, options) => write("/api/editorial/articles", "POST", data, options),
    updateArticle: (id, data, options) => write(`/api/editorial/articles/${id}`, "PATCH", data, options),
    deleteArticle: (id, options) => write(`/api/editorial/articles/${id}`, "DELETE", undefined, options),
    uploadCover: (file, options) => { const form = new FormData(); form.append("file", file); return write("/api/editorial/covers", "POST", form, options); },
    getDashboard: (options) => request("/api/management/dashboard", options),
    getFeaturedArticles: (page = 1, options) => request(`/api/articles?featured=1&page=${page}`, options),
    getHighlightCandidates: (page = 1, options) => request(`/api/management/highlights?page=${page}`, options),
    updateHighlight: (id, data, options) => write(`/api/management/highlights/${id}`, "PATCH", data, options),
    getManagementUsers: (page = 1, query = "", options) => request(`/api/management/users?page=${page}&q=${encodeURIComponent(query)}`, options),
    updateUserAccess: (id, is_active, options) => write(`/api/management/users/${id}`, "PATCH", { is_active }, options),
    getManagementSubscriptions: (page = 1, options) => request(`/api/management/subscriptions?page=${page}`, options),
    getManagementRequests: (page = 1, options) => request(`/api/management/requests?page=${page}`, options),
    resolveManagementRequest: (id, options) => write(`/api/management/requests/${id}`, "PATCH", { resolved: true }, options),
    getGroupSettings: (options) => request("/api/management/groups", options),
    createGroup: (data, options) => write("/api/management/groups", "POST", data, options),
    updateGroupSettings: (id, data, options) => write(`/api/management/groups/${id}`, "PATCH", data, options),
    getHealth: (options) => request("/api/health", options),
    getFounders: (options) => request("/api/founders", options),
    getManagedFounders: (options) => request("/api/management/founders", options),
    saveFounders: (data, options) => write("/api/management/founders", "PATCH", data, options),
    getReadiness: (options) => request("/api/ready", options),
    getMe: (options) => request("/api/auth/me", options),
    getPublicProfiles: (page = 1, query = "", role = "", options) => request(`/api/profiles?page=${page}&q=${encodeURIComponent(query)}&role=${encodeURIComponent(role)}`, options),
    getPublicProfile: (id, options) => request(`/api/profiles/${encodeURIComponent(id)}`, options),
    requestEmailChange: (data, options) => write("/api/auth/email", "POST", data, options),
    confirmEmailChange: (token, options) => write("/api/auth/email/confirm", "POST", { token }, options),
    login: (credentials, options) => write("/api/auth/login", "POST", credentials, options),
    logout: (options) => write("/api/auth/logout", "POST", {}, options),
    updateProfile: (profile, options) => write("/api/auth/me", "PATCH", profile, options),
    changePassword: (passwords, options) => write("/api/auth/password", "POST", passwords, options),
    getGroups: (page = 1, options) => request(`/api/groups?page=${page}`, options),
    getGroup: (slug, options) => request(`/api/groups/${encodeURIComponent(slug)}`, options),
    getColumnists: (page = 1, options) => request(`/api/facilitators?page=${page}`, options),
    getManagedGroups: (options) => request("/api/editorial/groups", options),
    getGroupMembers: (slug, options) => request(`/api/editorial/groups/${encodeURIComponent(slug)}/members`, options),
    addGroupMember: (slug, member, options) => write(`/api/editorial/groups/${encodeURIComponent(slug)}/members`, "POST", member, options),
    updateGroupMember: (slug, id, member, options) => write(`/api/editorial/groups/${encodeURIComponent(slug)}/members/${id}`, "PATCH", member, options),
    removeGroupMember: (slug, id, options) => write(`/api/editorial/groups/${encodeURIComponent(slug)}/members/${id}`, "DELETE", undefined, options),
  };
}
