FROM postgres:17

COPY 00_roles.sql /docker-entrypoint-initdb.d/00_roles.sql
COPY 01_bootstrap.sql /docker-entrypoint-initdb.d/01_bootstrap.sql