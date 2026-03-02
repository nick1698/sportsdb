\set ON_ERROR_STOP on

-- NOTE: only used to CREATE dbs
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'spdb_bootstrap') THEN
    CREATE ROLE spdb_bootstrap
      LOGIN
      PASSWORD 'spdb_bootstrap'
      CREATEDB;
  END IF;
END $$;

-- generic role with limited permissions
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'spdb_app') THEN
    CREATE ROLE spdb_app
      LOGIN
      PASSWORD 'spdb_app'
      NOSUPERUSER
      NOCREATEDB
      NOCREATEROLE;
  END IF;
END $$;