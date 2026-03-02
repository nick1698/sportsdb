-- generated: do not edit

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'volley_db') THEN
    CREATE DATABASE volley_db OWNER spdb_bootstrap;
  END IF;
END $$;

\connect volley_db
CREATE EXTENSION IF NOT EXISTS pgcrypto;

\connect postgres
GRANT CONNECT ON DATABASE volley_db TO spdb_app;