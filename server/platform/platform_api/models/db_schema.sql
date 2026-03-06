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
--
-- vertical_entity_id: UUID of the entity in the vertical DB.
-- ============================================================
CREATE TABLE
    IF NOT EXISTS org_sport_presence (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
        org_id uuid NOT NULL REFERENCES org (id) ON DELETE CASCADE,
        sport_key varchar(64) NOT NULL REFERENCES sport (key) ON DELETE RESTRICT,
        vertical_entity_id uuid NOT NULL,
        ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now (),
        CONSTRAINT uq_os_presence__org_sport_vertical UNIQUE (org_id, sport_key, vertical_entity_id)
    );

CREATE INDEX IF NOT EXISTS ix_os_presence__org_sport ON org_sport_presence (org_id, sport_key);

CREATE INDEX IF NOT EXISTS ix_os_presence__sport_vertical ON org_sport_presence (sport_key, vertical_entity_id);

CREATE TABLE
    IF NOT EXISTS person_sport_presence (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
        person_id uuid NOT NULL REFERENCES person (id) ON DELETE CASCADE,
        sport_key varchar(64) NOT NULL REFERENCES sport (key) ON DELETE RESTRICT,
        vertical_entity_id uuid NOT NULL,
        ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now (),
        CONSTRAINT uq_ps_presence__person_sport_vertical UNIQUE (person_id, sport_key, vertical_entity_id)
    );

CREATE INDEX IF NOT EXISTS ix_ps_presence__person_sport ON person_sport_presence (person_id, sport_key);

CREATE INDEX IF NOT EXISTS ix_ps_presence__sport_vertical ON person_sport_presence (sport_key, vertical_entity_id);

-- ============================================================
-- 8) INBOX (edit requests workflow)
-- payload: jsonb
-- status/action/entity_type are text with CHECK (easy to extend)
-- Context fields:
--   sport_key optional (FK)
--   (vertical_id here is an external id for the vertical system, not a FK)
-- ============================================================
CREATE TABLE
    IF NOT EXISTS edit_requests_inbox (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid (),
        entity_type varchar(16) NOT NULL CHECK (
            entity_type IN ('Org', 'Person', 'Venue', 'Location')
        ),
        action varchar(16) NOT NULL CHECK (action IN ('Create', 'Update', 'Merge')),
        status varchar(16) NOT NULL DEFAULT 'Pending' CHECK (
            status IN (
                'Pending',
                'Approved',
                'Rejected',
                'Duplicate',
                'Applied'
            )
        ),
        -- Context
        sport_key varchar(64) REFERENCES sport (key),
        vertical_entity_id uuid, -- external vertical/system id (not FK)
        target_entity_id uuid, -- Target for update/merge + nullable for create
        payload jsonb NOT NULL,
        -- Audit (can be nullable if auth not wired yet)
        created_by integer NOT NULL REFERENCES auth_user (id) ON DELETE RESTRICT,
        finalised_by integer REFERENCES auth_user (id) ON DELETE SET NULL,
        ts_taken_in_charge timestamptz,
        ts_review_completed timestamptz,
        review_notes text ts_creation timestamptz NOT NULL DEFAULT now (),
        ts_last_update timestamptz NOT NULL DEFAULT now (),
    );

CREATE INDEX ix_inbox_status_type ON edit_requests_inbox (status, entity_type);

CREATE INDEX ix_inbox_sport ON edit_requests_inbox (sport_key);

CREATE INDEX ix_inbox_target ON edit_requests_inbox (target_entity_id);

CREATE INDEX ix_inbox_vertical_entity ON edit_requests_inbox (vertical_entity_id);

CREATE TABLE
    edit_requests_inbox_event (
        id uuid PRIMARY KEY,
        request_id uuid NOT NULL REFERENCES edit_requests_inbox (id) ON DELETE CASCADE,
        event_type text NOT NULL CHECK (
            event_type IN (
                'Created',
                'Reviewed',
                'Approved',
                'Rejected',
                'Comment',
                'Applied'
            )
        ),
        actor integer NOT NULL REFERENCES auth_user (id) ON DELETE RESTRICT,
        notes text,

        ts_creation timestamptz NOT NULL,
        ts_last_update timestamptz NOT NULL
    );

CREATE INDEX ix_inbox_event__req_type ON edit_requests_inbox_event (request_id, event_type);