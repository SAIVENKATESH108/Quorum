import { neon, type NeonQueryFunction } from "@neondatabase/serverless";

function getDatabaseUrl(): string {
  return (
    process.env.DATABASE_URL ||
    process.env.POSTGRES_URL ||
    "postgresql://neondb_owner:npg_LZS35mcWrDBn@ep-falling-mud-b312nr2e-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
  );
}

let sqlInstance: NeonQueryFunction<false, false> | null = null;

export function getDb() {
  if (!sqlInstance) {
    const url = getDatabaseUrl();
    sqlInstance = neon(url);
  }
  return sqlInstance;
}
