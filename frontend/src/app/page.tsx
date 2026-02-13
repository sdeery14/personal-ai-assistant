import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default async function RootPage() {
  // Check if setup is needed
  try {
    const response = await fetch(`${API_BASE_URL}/auth/status`, {
      cache: "no-store",
    });
    const data = await response.json();

    if (data.setup_required) {
      redirect("/setup");
    }
  } catch {
    // If backend is down, still try to show login
  }

  // Check if user is authenticated
  const session = await auth();

  if (session) {
    redirect("/chat");
  }

  redirect("/login");
}
