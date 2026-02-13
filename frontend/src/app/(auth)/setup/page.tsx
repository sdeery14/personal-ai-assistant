"use client";

import { useEffect, useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Button, Input, Card } from "@/components/ui";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SetupPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    // Check if setup is needed
    fetch(`${API_BASE_URL}/auth/status`)
      .then((res) => res.json())
      .then((data) => {
        if (!data.setup_required) {
          router.replace("/login");
        }
        setChecking(false);
      })
      .catch(() => {
        setError("Cannot connect to the server");
        setChecking(false);
      });
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/setup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          password,
          display_name: displayName,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        setError(data.detail || "Setup failed");
        setIsLoading(false);
        return;
      }

      // Auto-login after setup
      const result = await signIn("credentials", {
        username,
        password,
        redirect: false,
      });

      if (result?.error) {
        setError("Setup succeeded but auto-login failed. Please go to login.");
      } else {
        router.push("/chat");
        router.refresh();
      }
    } catch {
      setError("An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (checking) {
    return (
      <Card padding="lg">
        <p className="text-center text-gray-500">Checking setup status...</p>
      </Card>
    );
  }

  return (
    <Card padding="lg">
      <h1 className="text-2xl font-bold text-gray-900 text-center mb-2">
        Welcome
      </h1>
      <p className="text-sm text-gray-600 text-center mb-6">
        Create your admin account to get started.
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Display Name"
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          required
          autoFocus
          placeholder="Your name"
        />
        <Input
          label="Username"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoComplete="username"
          minLength={3}
          placeholder="Choose a username"
        />
        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="new-password"
          minLength={8}
          placeholder="Minimum 8 characters"
        />
        {error && (
          <p className="text-sm text-red-600 text-center">{error}</p>
        )}
        <Button type="submit" className="w-full" isLoading={isLoading}>
          Create Admin Account
        </Button>
      </form>
    </Card>
  );
}
