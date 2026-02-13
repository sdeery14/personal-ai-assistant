"use client";

import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { apiClient, ApiError } from "@/lib/api-client";
import { User, CreateUserRequest } from "@/types/auth";
import { Button, Input, Card, Dialog } from "@/components/ui";

export default function AdminPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Create user form
  const [showCreate, setShowCreate] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [createError, setCreateError] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  // Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null);

  const isAdmin = (session?.user as { isAdmin?: boolean })?.isAdmin;

  const fetchUsers = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await apiClient.get<User[]>("/admin/users");
      setUsers(data);
    } catch {
      setError("Failed to load users");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAdmin) {
      router.replace("/chat");
      return;
    }
    fetchUsers();
  }, [isAdmin, router, fetchUsers]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError("");
    setIsCreating(true);

    try {
      const user = await apiClient.post<User>("/admin/users", {
        username: newUsername,
        password: newPassword,
        display_name: newDisplayName,
        is_admin: newIsAdmin,
      } satisfies CreateUserRequest);

      setUsers((prev) => [...prev, user]);
      setShowCreate(false);
      setNewUsername("");
      setNewPassword("");
      setNewDisplayName("");
      setNewIsAdmin(false);
    } catch (err) {
      if (err instanceof ApiError) {
        setCreateError(err.detail);
      } else {
        setCreateError("Failed to create user");
      }
    } finally {
      setIsCreating(false);
    }
  };

  const handleToggleActive = async (user: User) => {
    try {
      const updated = await apiClient.patch<User>(`/admin/users/${user.id}`, {
        is_active: !user.is_active,
      });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } catch {
      // silently fail
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiClient.del(`/admin/users/${deleteTarget.id}`);
      setUsers((prev) => prev.filter((u) => u.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      }
      setDeleteTarget(null);
    }
  };

  if (!isAdmin) return null;

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-4xl">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-semibold text-gray-900">
            User Management
          </h1>
          <Button onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? "Cancel" : "Create User"}
          </Button>
        </div>

        {error && (
          <p className="mb-4 text-sm text-red-600">{error}</p>
        )}

        {/* Create user form */}
        {showCreate && (
          <Card padding="md" className="mb-6">
            <form onSubmit={handleCreateUser} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="Display Name"
                  value={newDisplayName}
                  onChange={(e) => setNewDisplayName(e.target.value)}
                  required
                />
                <Input
                  label="Username"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  required
                  minLength={3}
                />
              </div>
              <Input
                label="Password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
              />
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={newIsAdmin}
                  onChange={(e) => setNewIsAdmin(e.target.checked)}
                  className="rounded"
                />
                Admin privileges
              </label>
              {createError && (
                <p className="text-sm text-red-600">{createError}</p>
              )}
              <Button type="submit" isLoading={isCreating}>
                Create
              </Button>
            </form>
          </Card>
        )}

        {/* User table */}
        {isLoading ? (
          <p className="text-sm text-gray-400">Loading users...</p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">User</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Username</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Role</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Created</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map((user) => (
                  <tr key={user.id} className="bg-white">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {user.display_name}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{user.username}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${
                          user.is_admin
                            ? "bg-purple-100 text-purple-700"
                            : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {user.is_admin ? "Admin" : "User"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${
                          user.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {user.is_active ? "Active" : "Disabled"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleToggleActive(user)}
                        >
                          {user.is_active ? "Disable" : "Enable"}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteTarget(user)}
                          className="text-red-500 hover:text-red-700"
                        >
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Dialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Delete user"
        description={`Are you sure you want to permanently delete ${deleteTarget?.display_name}? This cannot be undone.`}
        confirmLabel="Delete"
        confirmVariant="danger"
      />
    </div>
  );
}
