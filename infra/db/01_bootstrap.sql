\set ON_ERROR_STOP on

\echo '== SPDB bootstrap start =='

\i sql/10_platform_db.sql
\i sql/20_verticals.generated.sql

\echo '== SPDB bootstrap done =='