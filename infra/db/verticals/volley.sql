-- generated: do not edit

SELECT 'CREATE DATABASE volley_db OWNER spdb_bootstrap'
WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'volley_db'
)\gexec

\connect volley_db
CREATE EXTENSION IF NOT EXISTS pgcrypto;

\connect postgres
GRANT CONNECT ON DATABASE volley_db TO spdb_app;