import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      name: "credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) {
          return null;
        }

        try {
          const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              username: credentials.username,
              password: credentials.password,
            }),
          });

          if (!response.ok) {
            return null;
          }

          const data = await response.json();

          return {
            id: data.user.id,
            name: data.user.display_name,
            username: data.user.username,
            isAdmin: data.user.is_admin,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            expiresIn: data.expires_in,
          };
        } catch {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.username = (user as any).username;
        token.isAdmin = (user as any).isAdmin;
        token.accessToken = (user as any).accessToken;
        token.refreshToken = (user as any).refreshToken;
        token.accessTokenExpires = Date.now() + ((user as any).expiresIn * 1000);
      }

      // Return previous token if the access token has not expired yet
      if (Date.now() < (token.accessTokenExpires as number)) {
        return token;
      }

      // Access token expired — try to refresh
      try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: token.refreshToken }),
        });

        if (!response.ok) {
          return { ...token, error: "RefreshAccessTokenError" };
        }

        const data = await response.json();

        return {
          ...token,
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          accessTokenExpires: Date.now() + (data.expires_in * 1000),
          error: undefined,
        };
      } catch {
        return { ...token, error: "RefreshAccessTokenError" };
      }
    },
    async session({ session, token }) {
      return {
        ...session,
        user: {
          ...session.user,
          id: token.id as string,
          username: token.username as string,
          isAdmin: token.isAdmin as boolean,
        },
        accessToken: token.accessToken as string,
        error: token.error as string | undefined,
      };
    },
  },
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
});
