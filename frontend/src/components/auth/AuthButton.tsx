
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  getCurrentUser,
  loginWithGoogle,
  logout,
  type User,
} from "@/lib/auth";

interface AuthButtonProps {
  onAuthChange?: (user: User | null) => void;
}

export function AuthButton({
  onAuthChange,
}: AuthButtonProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCurrentUser()
      .then((currentUser) => {
        setUser(currentUser);
        onAuthChange?.(currentUser);
      })
      .catch(() => {
        setUser(null);
        onAuthChange?.(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [onAuthChange]);

  const handleLogout = async () => {
    try {
      await logout();
      setUser(null);
      onAuthChange?.(null);
    } catch {
      // Keep the current user state if logout fails.
    }
  };

  if (loading) {
    return (
      <Button
        variant="outline"
        size="sm"
        disabled
      >
        Loading...
      </Button>
    );
  }

  if (!user) {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={loginWithGoogle}
      >
        Sign in with Google
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {user.picture && (
        <img
          src={user.picture}
          alt={user.name ?? "User"}
          className="h-8 w-8 rounded-full"
        />
      )}

      <span className="hidden text-sm sm:inline">
        {user.name ?? user.email}
      </span>

      <Button
        variant="outline"
        size="sm"
        onClick={handleLogout}
      >
        Log out
      </Button>
    </div>
  );
}

