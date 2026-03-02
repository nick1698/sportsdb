-- Eseguito SOLO al primo bootstrap del volume (quando il data dir è vuoto).
-- Crea i DB separati per core/platform e per il vertical volley.
CREATE DATABASE platform_db;
CREATE DATABASE volley_db;

\connect platform_db;

-- used to generate random UUID
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;