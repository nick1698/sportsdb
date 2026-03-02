DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'platform_db') THEN
    CREATE DATABASE platform_db OWNER spdb_bootstrap;
  END IF;
END $$;

-- list extensions here:
\connect platform_db
CREATE EXTENSION IF NOT EXISTS pgcrypto;

\connect postgres
GRANT CONNECT ON DATABASE platform_db TO spdb_app;