import { createApiClient } from "./api-client.js";

// Caminhos relativos usam o domínio da página: rhemacuc.com.br em produção
// e o proxy local do Vite no computador. Nenhum endereço local entra no build.
export const api = createApiClient({ baseUrl: import.meta.env.VITE_API_BASE_URL?.trim() ?? "" });

export const getApiHealth = api.getHealth;
export const getApiReadiness = api.getReadiness;
