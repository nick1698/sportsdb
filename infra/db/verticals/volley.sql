-- generated: do not edit

SELECT 'CREATE DATABASE volley_w_db OWNER spdb_bootstrap'
WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'volley_w_db'
)\gexec

\connect volley_w_db
CREATE EXTENSION IF NOT EXISTS pgcrypto;
GRANT ALL PRIVILEGES ON SCHEMA public TO spdb_app;

\connect postgres
GRANT CONNECT ON DATABASE volley_w_db TO spdb_app;
GRANT ALL PRIVILEGES ON DATABASE volley_w_db TO spdb_app;
