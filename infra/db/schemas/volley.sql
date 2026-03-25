-- =========================================================
-- SPDB VOLLEY - FIRST MVP SCHEMA DRAFT
-- =========================================================
create domain url as varchar(256);

-- confederation
create table
    confederation (
        -- file: governance
        -- inherits: fixed
        id uuid primary key default gen_random_uuid (),
        acronym varchar(16) unique not null,
        name_local varchar(256) not null,
        name_en varchar(256),
        date_foundation date null,
        -- date_foundation: only nullable for MVP
        website url,
    );

-- federation
create table
    federation (
        -- file: governance
        -- inherits: fixed
        id uuid primary key,
        -- id: Not generated - logical hard-ref to platform.org
        confederation_id uuid not null references confederation (id),
        -- confederation_id: related_name: federations
        acronym varchar(16) unique not null,
        official_name varchar(256) unique not null,
        name_en varchar(256),
        date_foundation date null,
        -- date_foundation: only nullable for MVP
        website url,
        -- website: website of volley federation
    );

-- club
create table
    club (
        -- file: clubs
        id uuid primary key,
        -- id: Not generated - logical hard-ref to platform.org
        federation_id uuid not null references federation (id),
        -- federation_id: related_name: clubs
        acronym varchar(8) unique not null,
        short_name varchar(64) not null,
        official_name varchar(256) unique not null,
        date_foundation date null,
        -- date_foundation: Volley section foundation - only nullable for MVP
    );

create index idx_club__federation on club (federation_id);

create type hand as enum(
    'R', -- RIGHT
    'L', -- LEFT
    'A', -- AMBI
);

create type player_role as enum(
    'SET', -- SETTER
    'OH', -- OUTSIDE_HITTER
    'MB', -- MIDDLE_BLOCKER
    'OP', -- OPPOSITE_HITTER
    'LIB', -- LIBERO
    'DS', -- DEFENSIVE_SPECIALIST
);

-- athlete
create table
    athlete (
        -- file: athletes
        id uuid primary key,
        -- id: Not generated - logical hard-ref to platform.org
        dominant_hand hand not null default 'R',
        primary_role player_role not null,
        secondary_role player_role,
        career_start_date date null,
        -- career_start_date: only nullable for MVP
        date_retired date,
        jersey_nr_default integer,
        -- jersey_nr_default: verbose_name: Preferred jersey nr
        -- jersey_nr_default: validators: [MinValueValidator(1)]
        constraint chk_athlete__different_secondary_role check (
            secondary_role is null
            or secondary_role <> primary_role
        ),
        constraint chk_athlete__retirement_date check (
            career_start_date is null
            or date_retired is null
            or date_retired >= career_start_date
        ),
        constraint chk_athlete__jersey_nr_default check (
            jersey_nr_default is null
            or jersey_nr_default > 0
        )
    );

create type national_category as enum(
    'FST', -- FIRST
    'U22', -- U22
    'U21', -- U21
    'U19', -- U19
    'U17', -- U17
);

-- national_team: single category team of a federation
create table
    national_team (
        -- file: national
        -- djtitle: NatTeam
        id uuid primary key default gen_random_uuid (),
        federation_id uuid not null references federation (id),
        -- federation_id: related_name: national_teams
        category national_category not null default 'FST',
        constraint unq_national_team__federation_category unique (federation_id, category)
    );

-- athlete_national_team_presence: MVP summary table, not granular callup source of truth
create table
    athlete_national_team_presence (
        -- file: national
        -- djtitle: AthleteNatPresence
        -- verbose_name: Athlete calls for national teams
        -- verbose_name_plural: Athletes calls for national teams
        id uuid primary key default gen_random_uuid (),
        athlete_id uuid not null references athlete (id),
        -- athlete_id: related_name: called_for_national_team
        national_team_id uuid not null references national_team (id),
        -- national_team_id: related_name: athtlets_called
        first_callup_date date null,
        -- first_callup_date: only nullable for MVP
        last_callup_date date null,
        -- last_callup_date: only nullable for MVP
        constraint unq_nt_presence unique (athlete_id, national_team_id),
        constraint chk_nt_presence__callup_dates check (last_callup_date >= first_callup_date)
    );

-- NOTE: released = fired
create type contract_end_reason as enum(
    'EXPIRED', -- EXPIRED
    'TRANSFER', -- TRANSFER
    'RELEASED', -- RELEASED
    'MUT_TERM', -- MUTUAL_TERMINATION
    'RETIRED', -- RETIRED
    'OTHER', -- OTHER
    'UNKNOWN', -- UNKNOWN
);

-- athlete_club_contract
create table
    athlete_club_contract (
        -- file: athletes
        -- verbose_name: Athlete-Club contract
        id uuid primary key default gen_random_uuid (),
        athlete_id uuid not null references athlete (id),
        -- athlete_id: related_name: contracts_with_clubs
        club_id uuid not null references club (id),
        -- club_id: related_name: contracts_with_athletes
        loan_from_club_id uuid references club (id),
        -- loan_from_club_id: related_name: loans
        -- loan_from_club_id: on_delete: models.PROTECT
        -- loan_from_club_id: NOTE: if not null, the contract is a loan from this club
        duration daterange null,
        -- duration: only nullable for MVP
        end_reason contract_end_reason,
        -- end_reason: If null, the contract is still valid
        constraint chk_ath_club_ctr__different_loan_club check (
            loan_from_club_id is null
            or loan_from_club_id <> club_id
        ),
    );

create index idx_ath_club_ctr__athlete on athlete_club_contract (athlete_id);

create index idx_ath_club_ctr__club on athlete_club_contract (club_id);

-- season: general season table reused by club-side branch
create table
    season (
        -- file: governance
        id uuid primary key default gen_random_uuid (),
        duration daterange not null,
    );

create type club_category as enum(
    'FST', -- FIRST
    'U22', -- U22
    'U21', -- U21
    'U20', -- U20
    'U19', -- U19
    'U18', -- U18
    'U17', -- U17
);

-- club_team
create table
    club_team (
        -- file: clubs
        id uuid primary key default gen_random_uuid (),
        club_id uuid not null references club (id),
        -- club_id: related_name: teams
        category club_category not null DEFAULT 'FST',
        constraint unq_club_team__club_category unique (club_id, category)
    );

-- club_team_season
create table
    club_team_season (
        -- file: clubs
        -- verbose_name: Club seasonal team
        id uuid primary key default gen_random_uuid (),
        club_team_id uuid not null references club_team (id),
        -- club_team_id: related_name: seasons
        season_id uuid not null references season (id),
        -- season_id: related_name: club_teams
        -- season_id: on_delete: models.PROTECT
        constraint unq_club_team_season unique (club_team_id, season_id)
    );

-- club_team_season_athlete
create table
    club_team_season_athlete (
        -- file: athletes
        id uuid primary key default gen_random_uuid (),
        athlete_club_contract_id uuid not null references athlete_club_contract (id),
        -- athlete_club_contract_id: related_name: seasonal_team_contracts
        club_team_season_id uuid not null references club_team_season (id),
        -- club_team_season_id: related_name: seasonal_athlete_contracts
        jersey_nr integer null,
        -- jersey_nr: only nullable for MVP
        constraint unq_cts_ath__contract_team_season unique (athlete_club_contract_id, club_team_season_id),
        constraint chk_cts_ath__jersey_nr check (
            jersey_nr is null
            or (jersey_nr between 0 and 100)
        )
    );

-- league: national competition organizer delegated by a federation
create table
    league (
        -- file: governance
        id uuid primary key,
        -- id: Not generated - logical hard-ref to platform.org
        federation_id uuid not null references federation (id),
        -- federation_id: related_name: leagues
        acronym varchar(16) unique not null,
        official_name varchar(256) unique not null,
        name_en varchar(256),
        date_foundation date null,
        -- date_foundation: only nullable for MVP
        website url,
        -- website: website of the women's league
    );

create index idx_league__federation on league (federation_id);

-- competition
-- NOTE: 'LOC' -- LOCAL can be added later
create type competition_scope as enum(
    'INT', -- INTERNATIONAL
    'NAT', -- NATIONAL
);

-- TODO: review this
create type competition_type as enum(
    'champ', -- CHAMPIONSHIP
    'qual', -- QUALIFIERS
    'cup', -- CUP
    'trnmt', -- TOURNAMENT
    'frly' -- FRIENDLY
);

-- organizer_id semantics:
--   scope = national      -> organizer_id = league.id
--           international ->                confederation.id
create table
    competition (
        -- file: competitions
        id uuid primary key default gen_random_uuid (),
        "scope" competition_scope not null,
        organizer_id uuid not null,
        -- organizer_id: No foreign key - logical hard-ref to a volley organizer (confed or national league)
        "level" integer not null,
        -- level: from 1 to 99 = senior teams; from 100 to 199 = youth teams; from 200 = amateur teams
        "type" competition_type not null,
        official_name varchar(256) unique not null,
        short_name varchar(64) not null,
        acronym varchar(16) unique,
        date_foundation date null,
        -- date_foundation: only nullable for MVP
        constraint unq_competition__level unique ("scope", organizer_id, "level"),
    );

-- competition_season
create table
    competition_season (
        -- file: competitions
        id uuid primary key default gen_random_uuid (),
        competition_id uuid not null references competition (id),
        -- competition_id: related_name: seasons
        season_id uuid not null references season (id),
        -- season_id: related_name: competitions
        constraint unq_competition_season unique (competition_id, season_id)
    );

-- competition_season_team_entry
create type competition_phase as enum(
    'regular', -- REGULAR_SEASON
    'playout', -- PLAYOUT
    'playoff', -- PLAYOFF
    'final', -- FINAL
);

-- competition_season_team_entry: may later explode into phase tables
create table
    competition_season_team_entry (
        -- file: competitions
        id uuid primary key default gen_random_uuid (),
        club_team_season_id uuid not null references club_team_season (id),
        -- club_team_season_id: related_name: seasonal_competitions
        competition_season_id uuid not null references competition_season (id),
        -- club_team_season_id: related_name: seasonal_club_teams
        regular_season_points integer not null default 0,
        current_phase competition_phase default 'regular',
        constraint unq_competition_season_team_entry unique (club_team_season_id, competition_season_id),
    );

-- staff_member
CREATE TYPE staff_role AS ENUM(
    'head', -- HEAD_COACH
    'assist', -- ASSISTANT_COACH
    'tm', -- TEAM_MANAGER
    'sp_dir', -- SPORTING_DIRECTOR
    'tech_dir', -- TECHNICAL_DIRECTOR
    'gm', -- GENERAL_MANAGER
    'scout', -- SCOUT
    'stats', -- STATISTICIAN
    'ma', -- MATCH_ANALYST
    'cond_ch', -- STRENGTH_CONDITIONING_COACH
    'physio', -- PHYSIOTHERAPIST
    'doctor', -- DOCTOR
    'psycho', -- PSYCHOLOGIST
    'nutri', -- NUTRITIONIST
    'equipman', -- EQUIPMENT_MANAGER
    'mediaman', -- MEDIA_MANAGER
    'admin', -- ADMINISTRATION
    'other', -- OTHER
);

create table
    staff_member (
        -- file: staff
        id uuid primary key,
        -- id: Not generated - logical hard-ref to platform.org
        preferred_role staff_role not null default 'head',
    );

-- staff_club_contract: the staff member role does NOT live here - see team-season assignment table
create table
    staff_club_contract (
        -- file: staff
        id uuid primary key default gen_random_uuid (),
        staff_person_id uuid not null references staff_member (id),
        -- staff_person_id: related_name: club_contracts
        club_id uuid not null references club (id),
        -- club_id: related_name: staff_contracts
        duration daterange not null,
        -- duration: only nullable for MVP
        end_reason contract_end_reason,
    );

create index idx_staff_club_contract__staff on staff_club_contract (staff_person_id);

create index idx_staff_club_contract__club on staff_club_contract (club_id);

-- club_team_season_staff_role: staff role assignment to a specific club team in a specific season
create table
    club_team_season_staff_role (
        -- file: staff
        id uuid primary key default gen_random_uuid (),
        staff_club_contract_id uuid not null references staff_club_contract (id),
        -- staff_club_contract_id: related_name: seasonal_team_contracts
        club_team_season_id uuid not null references club_team_season (id),
        -- staff_club_contract_id: related_name: seasonal_staff_contrascts
        "role" staff_role not null,
        constraint unq_club_team_season_staff_role unique (
            staff_club_contract_id,
            club_team_season_id,
            "role"
        )
    );

create index idx_team_staff__contract on club_team_season_staff_role (staff_club_contract_id);

create index idx_team_staff__team on club_team_season_staff_role (club_team_season_id);

-- staff_federation_contract: contract is with federation, not directly with national_team
create table
    staff_federation_contract (
        -- file: staff
        id uuid primary key default gen_random_uuid (),
        staff_person_id uuid not null references staff_member (id),
        -- staff_person_id: related_name: federation_contracts
        federation_id uuid not null references federation (id),
        -- federation_id: related_name: sraff_contracts
        duration daterange not null,
        -- duration: only nullable for MVP
        end_reason contract_end_reason
    );

create index idx_staff_federation_contract__staff on staff_federation_contract (staff_person_id);

create index idx_staff_federation_contract__federation on staff_federation_contract (federation_id);

-- national_team_staff_role: staff role assignment under federation contract to a national team
create table
    national_team_staff_role (
        -- file: staff
        id uuid primary key default gen_random_uuid (),
        staff_federation_contract_id uuid not null references staff_federation_contract (id),
        -- staff_federation_contract_id: related_name: natioal_teams_roles
        national_team_id uuid not null references national_team (id),
        -- staff_federation_contract_id: related_name: federation_contracts
        "role" staff_role not null,
        constraint unq_national_team_staff_role unique (
            staff_federation_contract_id,
            national_team_id,
            "role"
        )
    );

create index idx_national_team_staff__contract on national_team_staff_role (staff_federation_contract_id);

create index idx_national_team_staff__national_team on national_team_staff_role (national_team_id);

-- executive
-- MVP intentionally minimal
create table
    executive (
        -- file: people
        id uuid primary key,
        -- id: Not generated - logical hard-ref to platform.org
    );


create type organisation_type as enum(
    'confed', -- CONFEDERATION
    'fed', -- FEDERATION
    'lg', -- LEAGUE
    'comp', -- COMPETITION
    'club', -- CLUB
);

create type executive_role as enum(
    'pres', -- PRESIDENT
    'vicpres', -- VICE-PRESIDENT
    'gen_man', -- GENERAL MANAGER
    'sp_dir', -- SPORTING DIRECTOR
    'tn_dir', -- TECHNICAL DIRECTOR
    'board_m', -- BOARD MEMBER
    'gen_sec', -- SECRETARY GENERAL
    'other' -- OTHER
);

-- executive_org_contract: org_type + org_id identify the target organization
create table
    executive_org_contract (
        -- file: people
        id uuid primary key default gen_random_uuid (),
        executive_person_id uuid not null references executive (id),
        -- executive_person_id: related_name: contracts
        org_type organisation_type not null,
        org_id uuid not null,
        -- org_id: No foreign key - logical hard-ref to the org type id
        role executive_role not null,
        duration daterange,
        end_reason contract_end_reason
    );
create index idx_executive_contract__person on executive_org_contract (executive_person_id);
create index idx_executive_contract__org on executive_org_contract (org_type, org_id);

-- referee
create table
    referee (
        -- file: people
        id uuid primary key,
        -- id: Not generated - logical hard-ref to platform.org
        federation_id uuid not null references federation (id),
        -- federation_id: related_name: referees
        license_level varchar(64),
        ref_category varchar(64),
        career_start_date date null, 
        -- career_start_date: only nullable for MVP
        date_retired date,
        constraint chk_referee_retired_after_start check (
            career_start_date is null
            or date_retired is null
            or date_retired >= career_start_date
        )
    );
create index idx_referee_federation on referee (federation_id);