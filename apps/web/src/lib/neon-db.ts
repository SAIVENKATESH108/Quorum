/**
 * Direct Neon database access from Next.js is strictly disabled.
 * All multi-tenant data operations must flow through the FastAPI backend
 * to ensure strict authentication, tenant scoping, and durable audit logs.
 */
export function getDb(): never {
  throw new Error(
    "Direct Neon database access from Next.js is disabled to protect tenant isolation. All data access must route through the FastAPI backend."
  );
}
