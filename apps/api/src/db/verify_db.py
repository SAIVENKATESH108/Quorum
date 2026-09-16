import asyncio
import asyncpg
from src.db.session import DATABASE_URL, connect_args


async def check_db() -> None:
    ssl = connect_args.get("ssl", None)
    raw_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(raw_url, ssl=ssl)

    print("\n" + "=" * 50)
    print("           PostgreSQL Extensions (\\dx)")
    print("=" * 50)
    extensions = await conn.fetch(
        """
        SELECT e.extname AS name, e.extversion AS version, n.nspname AS schema, c.description
        FROM pg_extension e
        LEFT JOIN pg_namespace n ON n.oid = e.extnamespace
        LEFT JOIN pg_description c ON c.objoid = e.oid AND c.classoid = 'pg_extension'::regclass
        ORDER BY e.extname;
        """
    )
    print(f"{'Name':<15} | {'Version':<10} | {'Schema':<10} | {'Description'}")
    print("-" * 65)
    for ext in extensions:
        desc = ext["description"] or ""
        print(f"{ext['name']:<15} | {ext['version']:<10} | {ext['schema']:<10} | {desc}")

    print("\n" + "=" * 50)
    print("           List of Relations (\\dt)")
    print("=" * 50)
    tables = await conn.fetch(
        """
        SELECT schemaname AS schema, tablename AS name, 'table' AS type, tableowner AS owner
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename;
        """
    )
    print(f"{'Schema':<10} | {'Name':<20} | {'Type':<8} | {'Owner'}")
    print("-" * 55)
    for t in tables:
        print(f"{t['schema']:<10} | {t['name']:<20} | {t['type']:<8} | {t['owner']}")

    print("\n" + "=" * 50)
    print("           Table Columns Verification")
    print("=" * 50)
    columns = await conn.fetch(
        """
        SELECT table_name, column_name, data_type, udt_name, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
        """
    )
    current_table = ""
    for col in columns:
        if col["table_name"] != current_table:
            current_table = col["table_name"]
            print(f"\nTable: {current_table}")
        dtype = col["udt_name"] if col["data_type"] == "USER-DEFINED" else col["data_type"]
        print(f"  - {col['column_name']:<20} {dtype:<15} (nullable: {col['is_nullable']})")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(check_db())
