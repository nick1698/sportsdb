\set ON_ERROR_STOP on

\echo '== SPDB bootstrap start =='

\i /db/10_platform.sql
\i /db/verticals/_index_.sql

\echo '== SPDB bootstrap done =='