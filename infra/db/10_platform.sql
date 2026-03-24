SELECT 'CREATE DATABASE platform_db OWNER spdb_bootstrap'
WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'platform_db'
)\gexec

-- list extensions here:
\connect platform_db
CREATE EXTENSION IF NOT EXISTS pgcrypto;
GRANT ALL PRIVILEGES ON SCHEMA public TO spdb_app;

\connect postgres
GRANT CONNECT ON DATABASE platform_db TO spdb_app;
GRANT ALL PRIVILEGES ON DATABASE platform_db TO spdb_app;
