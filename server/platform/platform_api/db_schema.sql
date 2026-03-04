-- ============================================================
-- PLATFORM DB (core identity) - DDL
-- Postgres
-- ============================================================
-- UUID generator
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- 1) COUNTRY
-- ============================================================
CREATE TABLE
    IF NOT EXISTS country (
        iso2 char(2) PRIMARY KEY,
        iso3 char(3) NOT NULL UNIQUE,
        numeric_code char(3) NOT NULL UNIQUE,
        name_en varchar(128) NOT NULL,
        name_local varchar(128),
        ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now ()
    );

-- ============================================================
-- 2) SPORT (ontology dictionary)
-- ============================================================
CREATE TABLE
    IF NOT EXISTS sport (
        key varchar(64) PRIMARY KEY, -- immutable slug
        name_en varchar(128) NOT NULL, -- display label (can evolve, key should not)
        description text,
        rules text,
        ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now ()
    );

-- ============================================================
-- 3) GEO_PLACE (country/region/city...)
-- ============================================================
CREATE TABLE
    IF NOT EXISTS geo_place (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
        country_id char(2) NOT NULL REFERENCES country (iso2),
        parent_id uuid REFERENCES geo_place (id),
        name varchar(128) NOT NULL,
        normalized_name varchar(128) NOT NULL UNIQUE,
        kind varchar(20) NOT NULL DEFAULT 'locality', -- not Postgres enum for MVP
        lat double precision, -- nullable for MVP
        lon double precision, -- nullable for MVP
        timezone varchar(8), -- nullable for MVP
        ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now (),
        CONSTRAINT chk_geo_place_latlon CHECK (
            (
                lat IS NULL
                AND lon IS NULL
            )
            OR (
                lat IS NOT NULL
                AND lon IS NOT NULL
            )
        ),
        CONSTRAINT unq_geo_place_country_parent_kind_normname UNIQUE (country_id, parent_id, kind, normalized_name)
    );

CREATE INDEX IF NOT EXISTS idx_geo_place_search ON geo_place (country_id, kind, normalized_name);

-- ============================================================
-- 4) VENUE (physical place used in sport)
-- ============================================================
CREATE TABLE
    IF NOT EXISTS venue (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
        name varchar(256) NOT NULL,
        short_name varchar(128),
        country_id char(2) NOT NULL REFERENCES country (iso2),
        geo_place_id uuid REFERENCES geo_place (id),
        address_line text, -- nullable for MVP
        postal_code varchar(16), -- nullable for MVP
        lat double precision, -- nullable for MVP
        lon double precision, -- nullable for MVP
        capacity integer, -- nullable for MVP
        date_opening date, -- nullable for MVP
        is_active boolean NOT NULL DEFAULT true,
        ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now (),
        CONSTRAINT chk_venue_latlon CHECK (
            (
                lat IS NULL
                AND lon IS NULL
            )
            OR (
                lat IS NOT NULL
                AND lon IS NOT NULL
            )
        )
    );

CREATE INDEX IF NOT EXISTS idx_venue_country_geoplace ON venue (country_id, geo_place_id);

-- ============================================================
-- 5) ORG (cross-sport organization)
-- ============================================================
CREATE TABLE
    IF NOT EXISTS org (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
        type smallint NOT NULL CHECK (type IN (1, 2)), -- no enum for MVP
        name varchar(128) NOT NULL,
        short_name varchar(64) NOT NULL,
        date_foundation date, -- nullable for MVP
        country_id char(2) NOT NULL REFERENCES country (iso2),
        home_geo_place_id uuid REFERENCES geo_place (id), -- nullable for MVP
        website varchar(256),
        is_active boolean NOT NULL DEFAULT true,
        ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now ()
    );

CREATE INDEX IF NOT EXISTS idx_org_country ON org (country_id);

-- ============================================================
-- 6) PERSON (cross-sport unique person identification)
-- ============================================================
CREATE TABLE
    IF NOT EXISTS person (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
        given_name varchar(128) NOT NULL,
        family_name varchar(128) NOT NULL,
        nickname varchar(128),
        sex smallint NOT NULL CHECK (sex IN (1, 2, 3)), -- no enum for MVP
        birth_date date, -- nullable for MVP
        birth_birth_geo_place_id uuid REFERENCES geo_place (id),
        death_date date,
        primary_nationality_id char(2) NOT NULL REFERENCES country (iso2),
        sporting_nationality_id char(2) REFERENCES country (iso2),
        ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now (),
        CONSTRAINT chk_person_death_after_birth CHECK (
            death_date IS NULL
            OR birth_date IS NULL
            OR death_date >= birth_date
        )
    );

CREATE INDEX IF NOT EXISTS idx_person_full_name ON person (family_name, given_name);

CREATE INDEX IF NOT EXISTS idx_person_primary_nat ON person (primary_nationality_id);

-- ============================================================
-- 7) PRESENCE (cross-DB identity mapping)
--
-- IMPORTANT: one-to-many mapping allowed:
--   platform person/org can map to multiple entities in the same vertical DB
-- So UNIQUE is on (platform_entity_id, sport_key, vertical_entity_id).
--
-- vertical_entity_id: UUID of the entity in the vertical DB.
-- vertical_key: textual identifier of the vertical (optional but useful for debugging/logging).
-- ============================================================
CREATE TABLE
    IF NOT EXISTS org_presence (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
        org_id uuid NOT NULL REFERENCES org (id) ON DELETE CASCADE,
        sport_key text NOT NULL REFERENCES sport (key),
        vertical_entity_id uuid NOT NULL, -- UUID in vertical DB
        vertical_key text NOT NULL, -- e.g. 'volleyball' (or any vertical identifier)
        is_active boolean NOT NULL DEFAULT true,
        ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now (),
        CONSTRAINT org_presence_uq UNIQUE (org_id, sport_key, vertical_entity_id)
    );

CREATE INDEX IF NOT EXISTS org_presence_sport_idx ON org_presence (sport_key);

CREATE INDEX IF NOT EXISTS org_presence_vertical_key_idx ON org_presence (vertical_key);

CREATE INDEX IF NOT EXISTS org_presence_org_idx ON org_presence (org_id);

CREATE TABLE
    IF NOT EXISTS person_presence (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
        person_id uuid NOT NULL REFERENCES person (id) ON DELETE CASCADE,
        sport_key text NOT NULL REFERENCES sport (key),
        vertical_entity_id uuid NOT NULL, -- UUID in vertical DB
        vertical_key text NOT NULL, -- e.g. 'volleyball'
        is_active boolean NOT NULL DEFAULT true,
        ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now (),
        CONSTRAINT person_presence_uq UNIQUE (person_id, sport_key, vertical_entity_id)
    );

CREATE INDEX IF NOT EXISTS person_presence_sport_idx ON person_presence (sport_key);

CREATE INDEX IF NOT EXISTS person_presence_vertical_key_idx ON person_presence (vertical_key);

CREATE INDEX IF NOT EXISTS person_presence_person_idx ON person_presence (person_id);

-- ============================================================
-- 8) INBOX (requests workflow)
-- payload: jsonb
-- status/action/entity_type are text with CHECK (easy to extend)
-- Context fields:
--   sport_key optional (FK) + vertical_key/vertical_id optional
--   (vertical_id here is an external id for the vertical system, not a FK)
-- ============================================================
CREATE TABLE
    IF NOT EXISTS inbox_request (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
        entity_type text NOT NULL CHECK (
            entity_type IN ('org', 'person', 'venue', 'geo_place')
        ),
        action text NOT NULL CHECK (action IN ('create', 'update', 'merge')),
        status text NOT NULL DEFAULT 'pending' CHECK (
            status IN ('pending', 'approved', 'rejected', 'applied')
        ),
        -- Context (optional)
        sport_key text REFERENCES sport (key),
        vertical_id uuid, -- external vertical/system id (not FK)
        vertical_key text, -- external vertical/system key
        -- Target for update/merge (nullable for create)
        target_entity_id uuid,
        payload jsonb NOT NULL,
        dedupe_key text,
        -- Audit (can be nullable if auth not wired yet)
        created_by_user_id uuid,
        reviewed_by_user_id uuid,
        ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now (),
        ts_reviewed timestamptz,
        review_note text
    );

CREATE INDEX IF NOT EXISTS inbox_request_status_idx ON inbox_request (status, ts_creation);

CREATE INDEX IF NOT EXISTS inbox_request_entity_idx ON inbox_request (entity_type, status);

CREATE INDEX IF NOT EXISTS inbox_request_sport_idx ON inbox_request (sport_key);

CREATE UNIQUE INDEX IF NOT EXISTS inbox_request_dedupe_uq ON inbox_request (dedupe_key)
WHERE
    dedupe_key IS NOT NULL;

CREATE TABLE
    IF NOT EXISTS inbox_request_event (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
        request_id uuid NOT NULL REFERENCES inbox_request (id) ON DELETE CASCADE,
        event_type text NOT NULL CHECK (
            event_type IN (
                'created',
                'approved',
                'rejected',
                'applied',
                'comment'
            )
        ),
        payload jsonb,
        ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now ()
    );

CREATE INDEX IF NOT EXISTS inbox_event_req_idx ON inbox_request_event (request_id, ts_creation);