-- =========================================================
-- SPDB VOLLEY - FIRST MVP SCHEMA DRAFT
-- =========================================================
create extension if not exists pgcrypto;

-- for UUIDs
-- ---------------------------------------------------------
-- confederation
-- ---------------------------------------------------------
create table
    confederation (
        id uuid primary key default gen_random_uuid (),
        acronym varchar(16) not null,
        name_local varchar(255) not null,
        name_en varchar(255),
        date_foundation date not null,
        website varchar(255),
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now ()
    );

-- ---------------------------------------------------------
-- federation
-- ---------------------------------------------------------
create table
    federation (
        id uuid primary key, -- logical hard-ref to platform.org = not generated
        confederation_id uuid not null references confederation (id),
        acronym varchar(32) not null,
        official_name varchar(255) not null,
        name_en varchar(255),
        founded_date date not null,
        website varchar(255),
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now ()
    );

-- ---------------------------------------------------------
-- club
-- ---------------------------------------------------------
create table
    club (
        id uuid primary key, -- logical hard-ref to platform.org = not generated
        federation_id uuid not null references confederation (id),
        acronym varchar(8) not null,
        short_name varchar(64) not null,
        official_name varchar(255) not null,
        founded_date date, -- only nullable for MVP
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now ()
    );

-- ---------------------------------------------------------
-- athlete
-- ---------------------------------------------------------
create table
    athlete (
        id uuid primary key, -- logical hard-ref to platform.person = not generated
        dominant_hand integer not null default 1, -- 1=right; 2=left; 3=ambi
        primary_role varchar(32) not null, -- will be an enum
        secondary_role varchar(32), -- will be an enum
        career_start_date date,
        date_retired date,
        jersey_nr_default integer,
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint ck_athlete_secondary_role_diff check (
            secondary_role is null
            or secondary_role <> primary_role
        ),
        constraint ck_athlete_retired_after_start check (
            career_start_date is null
            or date_retired is null
            or date_retired >= career_start_date
        ),
        constraint ck_athlete_jersey_nr_default check (
            jersey_nr_default is null
            or jersey_nr_default > 0
        )
    );

-- ---------------------------------------------------------
-- national_team
-- Single category team of a federation
-- ---------------------------------------------------------
create table
    national_team (
        id uuid primary key default gen_random_uuid (),
        federation_id uuid not null references federation (id),
        category varchar(64) not null, -- First team, U23, etc. - will become an enum
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint uq_national_team_federation_category unique (federation_id, category)
    );

-- ---------------------------------------------------------
-- athlete_national_team_presence
-- MVP summary table, not granular callup source of truth
-- ---------------------------------------------------------
create table
    athlete_national_team_presence (
        id uuid primary key default gen_random_uuid (),
        athlete_id uuid not null references athlete (id),
        national_team_id uuid not null references national_team (id),
        first_callup_date date not null,
        last_callup_date date not null,
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint uq_athlete_national_team_presence unique (athlete_id, national_team_id),
        constraint ck_nt_presence_dates check (last_callup_date >= first_callup_date)
    );

-- ---------------------------------------------------------
-- athlete_club_contract
-- NOTE:
-- loan_from_club_id: null = normal contract
--                    not null = player on loan at club_id from loan_from_club_id
-- ---------------------------------------------------------
create table
    athlete_club_contract (
        id uuid primary key default gen_random_uuid (),
        athlete_id uuid not null references athlete (id),
        club_id uuid not null references club (id),
        date_from date,
        date_to date,
        loan_from_club_id uuid references club (id),
        end_reason varchar(32), -- enum for both athletes and staff
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint ck_athlete_club_contract_dates check (
            date_from is null
            or date_to is null
            or date_to >= date_from
        ),
        constraint ck_athlete_club_contract_loan_from_diff check (
            loan_from_club_id is null
            or loan_from_club_id <> club_id
        ),
        constraint ck_athlete_club_contract_end_reason check (
            end_reason in (
                'expired',
                'transfer',
                'released',
                'mutual_termination',
                'retired',
                'other',
                'unknown'
            )
            or end_reason is null
        )
    );

create index idx_athlete_club_contract_athlete on athlete_club_contract (athlete_id);

create index idx_athlete_club_contract_club on athlete_club_contract (club_id);

-- ---------------------------------------------------------
-- season
-- general season table reused by club-side branch
-- ---------------------------------------------------------
create table
    season (
        id uuid primary key default gen_random_uuid (),
        start_date date not null,
        end_date date not null,
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint ck_season_dates check (end_date > start_date)
    );

-- ---------------------------------------------------------
-- club_team
-- ---------------------------------------------------------
create table
    club_team (
        id uuid primary key default gen_random_uuid (),
        club_id uuid not null references club (id),
        category varchar(64) not null,
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint uq_club_team_club_category unique (club_id, category)
    );

-- ---------------------------------------------------------
-- club_team_season
-- ---------------------------------------------------------
create table
    club_team_season (
        id uuid primary key default gen_random_uuid (),
        club_team_id uuid not null references club_team (id),
        season_id uuid not null references season (id),
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint uq_club_team_season unique (club_team_id, season_id)
    );

-- ---------------------------------------------------------
-- club_team_season_roster_entry
-- ---------------------------------------------------------
create table
    club_team_season_roster_entry (
        id uuid primary key default gen_random_uuid (),
        athlete_club_contract_id uuid not null references athlete_club_contract (id),
        club_team_season_id uuid not null references club_team_season (id),
        jersey_nr integer, -- only nullable for MVP
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint uq_roster_entry_contract_team_season unique (athlete_club_contract_id, club_team_season_id),
        constraint ck_roster_entry_jersey_nr check (
            jersey_nr is null
            or jersey_nr > 0
        )
    );

-- ---------------------------------------------------------
-- competition
-- organizer_id semantics:
--   scope = national      -> organizer_id = federation.id
--           international ->                confederation.id
-- ---------------------------------------------------------
create table
    competition (
        id uuid primary key default gen_random_uuid (),
        scope varchar(32) not null,
        competition_type varchar(32) not null, -- national/international enum; will include "local" later?
        organizer_id uuid not null,
        official_name varchar(255) not null,
        short_name varchar(255) not null,
        acronym varchar(16),
        level integer not null, -- from 1 to 99 = senior teams; from 100 to 199 = youth teams; from 200 = amateur teams
        founded_date date, -- nullable for MVP
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint ck_competition_scope check (scope in ('national', 'international')),
        constraint uq_competition_official_name unique (scope, organizer_id, official_name),
        constraint uq_competition_level unique (scope, organizer_id, level)
    );

-- ---------------------------------------------------------
-- competition_season
-- ---------------------------------------------------------
create table
    competition_season (
        id uuid primary key default gen_random_uuid (),
        competition_id uuid not null references competition (id),
        season_id uuid not null references season (id),
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint uq_competition_season unique (competition_id, season_id)
    );

-- ---------------------------------------------------------
-- competition_season_team_entry
-- MVP summary fields that may later explode into phase tables
-- ---------------------------------------------------------
create table
    competition_season_team_entry (
        id uuid primary key default gen_random_uuid (),
        club_team_season_id uuid not null references club_team_season (id),
        competition_season_id uuid not null references competition_season (id),
        regular_season_points integer not null default 0,
        current_phase varchar(32),
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint uq_competition_season_team_entry unique (club_team_season_id, competition_season_id),
        constraint ck_competition_season_team_entry_phase check (
            current_phase in (
                'regular_season',
                'playoff',
                'playout',
                'final_phase',
                'finished'
            )
            or current_phase is null
        )
    );

-- ---------------------------------------------------------
-- staff_member
-- preferred_role = preferred/main professional role, not the role on contracts/assignments
-- ---------------------------------------------------------
create table
    staff_member (
        id uuid primary key,  -- logical hard-ref to platform.person
        preferred_role varchar(64),
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now ()
    );

-- ---------------------------------------------------------
-- staff_club_contract
-- logical contract between staff member and club
-- staff_role does NOT live here, but in team-season assignment tables
-- ---------------------------------------------------------
create table
    staff_club_contract (
        id uuid primary key default gen_random_uuid (),
        staff_person_id uuid not null references staff_member (id),
        club_id uuid not null references club (id),
        date_from date,
        date_to date,
        end_reason varchar(32), -- enum for both athletes and staff
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint ck_staff_club_contract_dates check (
            date_from is null
            or date_to is null
            or date_to >= date_from
        ),
        constraint ck_staff_club_contract_end_reason check (
            end_reason in (
                'expired',
                'transfer',
                'released',
                'mutual_termination',
                'retired',
                'other',
                'unknown'
            )
            or end_reason is null
        )
    );

create index idx_staff_club_contract_staff on staff_club_contract (staff_person_id);

create index idx_staff_club_contract_club on staff_club_contract (club_id);

-- ---------------------------------------------------------
-- club_team_season_staff_entry
-- concrete staff assignment to a specific club team in a specific season
-- staff_role lives here
-- ---------------------------------------------------------
create table
    club_team_season_staff_entry (
        id uuid primary key default gen_random_uuid (),
        staff_club_contract_id uuid not null references staff_club_contract (id),
        club_team_season_id uuid not null references club_team_season (id),
        staff_role varchar(64) not null, -- will become an enum?
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint uq_club_team_season_staff_entry unique (
            staff_club_contract_id,
            club_team_season_id,
            staff_role
        )
    );

create index idx_club_team_season_staff_entry_contract on club_team_season_staff_entry (staff_club_contract_id);

create index idx_club_team_season_staff_entry_team_season on club_team_season_staff_entry (club_team_season_id);

-- ---------------------------------------------------------
-- staff_federation_contract
-- contract is with federation, not directly with national_team
-- staff_role does NOT live here, but in national_team assignment table
-- ---------------------------------------------------------
create table
    staff_federation_contract (
        id uuid primary key default gen_random_uuid (),
        staff_person_id uuid not null references staff_member (id),
        federation_id uuid not null references federation (id),
        date_from date,
        date_to date,
        end_reason varchar(32), -- enum for both athletes and staff
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint ck_staff_federation_contract_dates check (
            date_from is null
            or date_to is null
            or date_to >= date_from
        ),
        constraint ck_staff_federation_contract_end_reason check (
            end_reason in (
                'expired',
                'transfer',
                'released',
                'mutual_termination',
                'retired',
                'other',
                'unknown'
            )
            or end_reason is null
        )
    );

create index idx_staff_federation_contract_staff on staff_federation_contract (staff_person_id);

create index idx_staff_federation_contract_federation on staff_federation_contract (federation_id);

-- ---------------------------------------------------------
-- national_team_staff_assignment
-- concrete assignment of staff under federation contract to a national team
-- staff_role lives here
-- ---------------------------------------------------------
create table
    national_team_staff_assignment (
        id uuid primary key default gen_random_uuid (),
        staff_federation_contract_id uuid not null references staff_federation_contract (id),
        national_team_id uuid not null references national_team (id),
        staff_role varchar(64) not null, -- will become an enum?
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint uq_national_team_staff_assignment unique (
            staff_federation_contract_id,
            national_team_id,
            staff_role
        )
    );

create index idx_national_team_staff_assignment_contract on national_team_staff_assignment (staff_federation_contract_id);

create index idx_national_team_staff_assignment_national_team on national_team_staff_assignment (national_team_id);

-- ---------------------------------------------------------
-- executive
-- MVP intentionally minimal
-- ---------------------------------------------------------
create table
    executive (
        id uuid primary key, -- logical hard-ref to platform.person
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now ()
    );

-- ---------------------------------------------------------
-- executive_org_contract
-- unified historical table without hard FK to target org type
-- org_type + org_id identify the target organization logically
-- ---------------------------------------------------------
create table
    executive_org_contract (
        id uuid primary key default gen_random_uuid (),
        executive_person_id uuid not null references executive (id),
        org_type varchar(32) not null,
        org_id uuid not null,
        role varchar(64) not null, -- will become an enum?
        date_from date,
        date_to date,
        end_reason varchar(32), -- different enum from athletes and staff
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint ck_executive_org_contract_org_type check (
            org_type in ('club', 'federation', 'confederation', 'other')
        ),
        -- constraint ck_executive_org_contract_role check (
        --     role in (
        --         'president',
        --         'vice_president',
        --         'general_manager',
        --         'sporting_director',
        --         'board_member',
        --         'secretary_general',
        --         'other'
        --     )
        -- ),
        constraint ck_executive_org_contract_dates check (
            date_from is null
            or date_to is null
            or date_to >= date_from
        ),
        constraint ck_executive_org_contract_end_reason check (
            end_reason in (
                'expired',
                'released',
                'mutual_termination',
                'retired',
                'other',
                'unknown'
            )
            or end_reason is null
        )
    );

create index idx_executive_org_contract_executive on executive_org_contract (executive_person_id);

create index idx_executive_org_contract_org on executive_org_contract (org_type, org_id);

-- ---------------------------------------------------------
-- referee
-- MVP simplification: direct federation reference, no historical affiliation table
-- ---------------------------------------------------------
create table
    referee (
        id uuid primary key, -- logical hard-ref to platform.person
        federation_id uuid not null references federation (id),
        license_level varchar(64),
        ref_category varchar(64),
        career_start_date date, -- only nullable for MVP
        date_retired date,
        ts_creation timestamptz not null default now (),
        ts_last_update timestamptz not null default now (),
        constraint ck_referee_retired_after_start check (
            career_start_date is null
            or date_retired is null
            or date_retired >= career_start_date
        )
    );

create index idx_referee_federation on referee (federation_id);