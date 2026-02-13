export interface User {
  id: string;
  username: string;
  display_name: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}

export interface SetupRequest {
  username: string;
  password: string;
  display_name: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface CreateUserRequest {
  username: string;
  password: string;
  display_name: string;
  is_admin?: boolean;
}

export interface UpdateUserRequest {
  display_name?: string;
  is_active?: boolean;
  password?: string;
}

export interface AuthStatus {
  setup_required: boolean;
}
