try:
        rows = session.sql(
            """
            select
              current_account() as account,
              current_user() as user_name,
              current_role() as role_name,
              current_warehouse() as warehouse_name,
              current_database() as database_name,
              current_schema() as schema_name
            """
        ).collect()
    except Exception as exc:
        print(f"FAILED: connected but validation query did not run: {exc}")
        session.close()
        return 1

    row = rows[0]
    print("Snowpark connection OK")
    print(f"account={row['ACCOUNT']}")
    print(f"user={row['USER_NAME']}")
    print(f"role={row['ROLE_NAME']}")
    print(f"warehouse={row['WAREHOUSE_NAME']}")
    print(f"database={row['DATABASE_NAME']}")
    print(f"schema={row['SCHEMA_NAME']}")
    session.close()
