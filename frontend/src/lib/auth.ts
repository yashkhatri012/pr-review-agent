
export interface User {
  id: string;
  email: string | null;
  name: string | null;
  picture: string | null;
  free_review_used: boolean;
}

const API_URL = import.meta.env.VITE_API_URL;

export function loginWithGoogle(): void {
  window.location.href = `${API_URL}/api/auth/google`;
}

export async function getCurrentUser(): Promise<User | null> {
  const response = await fetch(`${API_URL}/api/auth/me`, {
    credentials: "include",
  });

  if (response.status === 401) {
    return null;
  }

  if (!response.ok) {
    throw new Error("Failed to fetch authenticated user.");
  }

  return response.json();
}

export async function logout(): Promise<void> {
  const response = await fetch(`${API_URL}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Failed to log out.");
  }
}

