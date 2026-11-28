import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import AdminDashboard from "./AdminDashboard";

export default async function AdminPage() {
  const jar = await cookies();
  if (!jar.get("km_access") && !jar.get("km_refresh")) redirect("/login");
  return <AdminDashboard />;
}
