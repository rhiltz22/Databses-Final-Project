-- ============================================================
-- CS 5330 Group Project — Social Media Analysis Database
-- MySQL Schema
-- ============================================================

-- Drop tables in reverse dependency order for clean re-runs
DROP TABLE IF EXISTS AnalysisResult;
DROP TABLE IF EXISTS Field;
DROP TABLE IF EXISTS Post;
DROP TABLE IF EXISTS UserAccount;
DROP TABLE IF EXISTS Project;
DROP TABLE IF EXISTS Institution;
DROP TABLE IF EXISTS Platform;
DROP TABLE IF EXISTS Person;

-- ------------------------------------------------------------
-- Person
-- Represents a real individual who may own multiple accounts.
-- unique_id is auto-generated; name may be unknown.
-- ------------------------------------------------------------
CREATE TABLE Person (
    unique_id       INT             NOT NULL AUTO_INCREMENT,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    PRIMARY KEY (unique_id)
);

-- ------------------------------------------------------------
-- Platform
-- A social media platform (e.g. Twitter, Facebook).
-- ------------------------------------------------------------
CREATE TABLE Platform (
    platform_name   VARCHAR(100)    NOT NULL,
    PRIMARY KEY (platform_name)
);

-- ------------------------------------------------------------
-- Institution
-- Research institution that manages projects.
-- ------------------------------------------------------------
CREATE TABLE Institution (
    institution_name    VARCHAR(200)    NOT NULL,
    PRIMARY KEY (institution_name)
);

-- ------------------------------------------------------------
-- Project
-- A research project that analyzes social media posts.
-- end_date must be >= start_date (enforced by CHECK constraint).
-- ------------------------------------------------------------
CREATE TABLE Project (
    project_name        VARCHAR(200)    NOT NULL,
    manager_first_name  VARCHAR(100),
    manager_last_name   VARCHAR(100),
    start_date          DATE,
    end_date            DATE,
    institution_name    VARCHAR(200)    NOT NULL,
    PRIMARY KEY (project_name),
    FOREIGN KEY (institution_name)
        REFERENCES Institution(institution_name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT chk_project_dates
        CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

-- ------------------------------------------------------------
-- UserAccount (Weak entity — identified by username + platform)
-- A social media account. May optionally be linked to a Person.
-- username is at most 40 characters per spec.
-- ------------------------------------------------------------
CREATE TABLE UserAccount (
    username            VARCHAR(40)     NOT NULL,
    platform_name       VARCHAR(100)    NOT NULL,
    unique_id           INT,                        -- nullable: not all accounts are linked
    first_name          VARCHAR(100),
    last_name           VARCHAR(100),
    country_of_birth    VARCHAR(100),
    country_of_residence VARCHAR(100),
    age                 TINYINT UNSIGNED,
    gender              VARCHAR(50),
    verification_status BOOLEAN         DEFAULT FALSE,
    PRIMARY KEY (username, platform_name),
    FOREIGN KEY (platform_name)
        REFERENCES Platform(platform_name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (unique_id)
        REFERENCES Person(unique_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- Post
-- A social media text post. May be a repost of another post.
-- A user cannot post twice to the same platform at the exact
-- same time — enforced by the PK on (username, platform_name, time).
-- post_id is a surrogate key for foreign key references.
-- ------------------------------------------------------------
CREATE TABLE Post (
    post_id             INT             NOT NULL AUTO_INCREMENT,
    username            VARCHAR(40)     NOT NULL,
    platform_name       VARCHAR(100)    NOT NULL,
    posted_at           DATETIME        NOT NULL,   -- year/month/day/hour/minute
    text_content        TEXT            NOT NULL,
    city                VARCHAR(100),
    state               VARCHAR(100),
    country             VARCHAR(100),
    num_likes           INT UNSIGNED,
    num_dislikes        INT UNSIGNED,
    contains_multimedia BOOLEAN,
    repost_of_post_id   INT,                        -- nullable: NULL means original post
    PRIMARY KEY (post_id),
    -- A user cannot have two posts on the same platform at the same minute
    UNIQUE KEY uq_post_time (username, platform_name, posted_at),
    FOREIGN KEY (username, platform_name)
        REFERENCES UserAccount(username, platform_name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (repost_of_post_id)
        REFERENCES Post(post_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- Field (Weak entity — identified by field_name + project_name)
-- Defines the output fields for a given project.
-- Field names are unique within a project.
-- ------------------------------------------------------------
CREATE TABLE Field (
    field_name      VARCHAR(200)    NOT NULL,
    project_name    VARCHAR(200)    NOT NULL,
    PRIMARY KEY (field_name, project_name),
    FOREIGN KEY (project_name)
        REFERENCES Project(project_name)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- AnalysisResult
-- Stores the value of a field for a specific post in a project.
-- Partial results are allowed — not every (post, field) pair
-- needs to be populated.
-- ------------------------------------------------------------
CREATE TABLE AnalysisResult (
    project_name    VARCHAR(200)    NOT NULL,
    post_id         INT             NOT NULL,
    field_name      VARCHAR(200)    NOT NULL,
    field_value     TEXT,
    PRIMARY KEY (project_name, post_id, field_name),
    FOREIGN KEY (project_name)
        REFERENCES Project(project_name)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (post_id)
        REFERENCES Post(post_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (field_name, project_name)
        REFERENCES Field(field_name, project_name)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- Indexes for common query filters (scale/read performance)
-- ------------------------------------------------------------
CREATE INDEX idx_post_platform_posted_at ON Post (platform_name, posted_at);
CREATE INDEX idx_post_posted_at ON Post (posted_at);
CREATE INDEX idx_useraccount_name ON UserAccount (last_name, first_name);

-- ------------------------------------------------------------
-- Optional partitioning (not enabled by default)
-- Use only if data grows very large and you accept table changes.
-- Example (MySQL 8+):
-- ALTER TABLE Post
-- PARTITION BY RANGE (YEAR(posted_at)) (
--   PARTITION p2024 VALUES LESS THAN (2025),
--   PARTITION p2025 VALUES LESS THAN (2026),
--   PARTITION pmax VALUES LESS THAN MAXVALUE
-- );
