-- generated: do not edit

SELECT 'CREATE DATABASE volley_w_db OWNER spdb_bootstrap'
WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'volley_w_db'
)\gexec

\connect volley_w_db
CREATE EXTENSION IF NOT EXISTS pgcrypto;

\connect postgres
GRANT CONNECT ON DATABASE volley_db TO spdb_app;