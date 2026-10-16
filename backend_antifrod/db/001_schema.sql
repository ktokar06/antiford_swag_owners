CREATE TABLE app_user (
    id             SERIAL PRIMARY KEY,
    email          VARCHAR(200) NOT NULL UNIQUE,
    password_hash  VARCHAR(200) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'operator'
        CHECK (role = 'operator'),
    full_name      VARCHAR(200),
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_login_at  TIMESTAMPTZ
);

CREATE TABLE user_avatar (
    user_id INTEGER PRIMARY KEY REFERENCES app_user(id) ON DELETE CASCADE,
    image BYTEA NOT NULL
);

CREATE TABLE password_reset_token (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    token       VARCHAR(128) NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_prt_token ON password_reset_token(token);

CREATE TABLE country (
    id          SMALLSERIAL PRIMARY KEY,
    iso_code    CHAR(2)     NOT NULL UNIQUE,
    name        VARCHAR(100) NOT NULL
);

CREATE TABLE region (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10) NOT NULL UNIQUE,
    name        VARCHAR(120) NOT NULL,
    country_id  SMALLINT NOT NULL REFERENCES country(id)
);

CREATE TABLE operator (
    id           SERIAL PRIMARY KEY,
    code         VARCHAR(10) NOT NULL UNIQUE,
    name         VARCHAR(120) NOT NULL,
    is_home      BOOLEAN NOT NULL DEFAULT FALSE,
    country_id   SMALLINT NOT NULL REFERENCES country(id)
);

CREATE TABLE connection_type (
    id      SMALLSERIAL PRIMARY KEY,
    code    VARCHAR(20) NOT NULL UNIQUE,
    name    VARCHAR(60) NOT NULL
);

CREATE TABLE call_direction (
    id      SMALLSERIAL PRIMARY KEY,
    code    VARCHAR(20) NOT NULL UNIQUE,
    name    VARCHAR(60) NOT NULL
);

CREATE TABLE time_bucket (
    id        SMALLSERIAL PRIMARY KEY,
    code      VARCHAR(20) NOT NULL UNIQUE,
    label     VARCHAR(60) NOT NULL,
    hour_from SMALLINT NOT NULL CHECK (hour_from BETWEEN 0 AND 23),
    hour_to   SMALLINT NOT NULL CHECK (hour_to   BETWEEN 0 AND 24)
);

CREATE TABLE number_kind (
    id      SMALLSERIAL PRIMARY KEY,
    code    VARCHAR(20) NOT NULL UNIQUE,
    name    VARCHAR(60) NOT NULL
);

CREATE TABLE subscriber (
    id           SERIAL PRIMARY KEY,
    external_id  VARCHAR(64),
    full_name    VARCHAR(200),
    kind         VARCHAR(20) NOT NULL DEFAULT 'person'
                 CHECK (kind IN ('person','company')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE phone_number (
    id              SERIAL PRIMARY KEY,
    number          CHAR(10)   NOT NULL UNIQUE,
    subscriber_id   INTEGER    REFERENCES subscriber(id),
    region_code     VARCHAR(10),
    operator_code   VARCHAR(10),
    kind            VARCHAR(20) NOT NULL DEFAULT 'unknown',
    is_valid        BOOLEAN    NOT NULL DEFAULT TRUE,
    invalid_reason  VARCHAR(120),
    first_seen      TIMESTAMPTZ,
    last_seen       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_phone_number_number     ON phone_number(number);
CREATE INDEX idx_phone_number_subscriber ON phone_number(subscriber_id);
CREATE INDEX idx_phone_number_valid      ON phone_number(is_valid);

CREATE TABLE cdr_file (
    id           SERIAL PRIMARY KEY,
    filename     VARCHAR(200) NOT NULL UNIQUE,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    rows_valid   INTEGER NOT NULL DEFAULT 0,
    rows_invalid INTEGER NOT NULL DEFAULT 0,
    checksum CHAR(64),
    source VARCHAR(20) NOT NULL DEFAULT 'directory',
    status VARCHAR(30) NOT NULL DEFAULT 'loaded',
    rows_total INTEGER NOT NULL DEFAULT 0,
    rows_duplicate INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE invalid_cdr_row (
    id          BIGSERIAL PRIMARY KEY,
    cdr_file_id INTEGER REFERENCES cdr_file(id),
    row_num     INTEGER,
    error_code VARCHAR(40),
    fields_found INTEGER,
    raw_line    TEXT NOT NULL,
    reason      VARCHAR(200) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE call_record (
    id                     BIGSERIAL PRIMARY KEY,
    cdr_file_id            INTEGER REFERENCES cdr_file(id),
    row_num                INTEGER,
    row_hash               CHAR(64),
    type                   CHAR(2)  NOT NULL,
    imsi                   CHAR(15),
    caller_number          CHAR(10) NOT NULL,
    callee_number          CHAR(10) NOT NULL,
    forward_number         CHAR(10),
    started_at             TIMESTAMPTZ NOT NULL,
    duration_sec           INTEGER NOT NULL DEFAULT 0 CHECK (duration_sec >= 0),
    hung_up_first_second   BOOLEAN NOT NULL DEFAULT FALSE,
    direction              VARCHAR(20),
    connection_type        VARCHAR(20),
    time_bucket            VARCHAR(20),
    source_country         VARCHAR(2),
    source_operator        VARCHAR(10),
    foreign_origin         BOOLEAN NOT NULL DEFAULT FALSE,
    is_valid               BOOLEAN NOT NULL DEFAULT TRUE,
    invalid_reason         VARCHAR(200),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_call_started_at ON call_record(started_at);
CREATE INDEX idx_call_caller     ON call_record(caller_number);
CREATE INDEX idx_call_callee     ON call_record(callee_number);
CREATE INDEX idx_call_imsi       ON call_record(imsi);
CREATE INDEX idx_call_type       ON call_record(type);
CREATE INDEX idx_call_valid      ON call_record(is_valid);

CREATE TABLE call_feature (
    call_record_id        BIGINT PRIMARY KEY
                          REFERENCES call_record(id) ON DELETE CASCADE,
    call_count            INTEGER,
    call_sum_dur          BIGINT,
    call_min_dur          INTEGER,
    call_max_dur          INTEGER,
    call_mean_dur         NUMERIC(10,2),
    call_median_dur       NUMERIC(10,2),
    call_std_dur          NUMERIC(10,2),
    call_var_dur          NUMERIC(12,2),
    call_skewness_dur     NUMERIC(10,4),
    call_kurtosis_dur     NUMERIC(10,4),
    window_5_count        INTEGER,
    window_5_sum_dur      BIGINT,
    window_10_count       INTEGER,
    window_30_count       INTEGER,
    window_60_count       INTEGER,
    window_300_count      INTEGER,
    computed_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE number_feature (
    phone_number_id         INTEGER PRIMARY KEY
                            REFERENCES phone_number(id) ON DELETE CASCADE,
    window_days             INTEGER NOT NULL DEFAULT 5,
    total_calls             INTEGER NOT NULL DEFAULT 0,
    outgoing_calls          INTEGER NOT NULL DEFAULT 0,
    calls_per_hour          INTEGER NOT NULL DEFAULT 0,
    unique_counterparts     INTEGER NOT NULL DEFAULT 0,
    region_reach            INTEGER NOT NULL DEFAULT 0,
    short_call_share        NUMERIC(5,4) NOT NULL DEFAULT 0,
    unanswered_share        NUMERIC(5,4) NOT NULL DEFAULT 0,
    has_incoming            BOOLEAN NOT NULL DEFAULT FALSE,
    has_outgoing            BOOLEAN NOT NULL DEFAULT FALSE,
    has_forwarded           BOOLEAN NOT NULL DEFAULT FALSE,
    numbers_per_subscriber  INTEGER NOT NULL DEFAULT 1,
    max_risk_score          INTEGER NOT NULL DEFAULT 0,
    avg_risk_score          NUMERIC(6,2) NOT NULL DEFAULT 0,
    has_fan_pattern         BOOLEAN NOT NULL DEFAULT FALSE,
    fan_group               VARCHAR(120),
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE graph_cluster (
    id              SERIAL PRIMARY KEY,
    label           VARCHAR(120) NOT NULL,
    pattern         VARCHAR(40)  NOT NULL,
    risk_level      VARCHAR(10)  NOT NULL DEFAULT 'low'
                    CHECK (risk_level IN ('low','medium','high')),
    template        TEXT,
    number_count    INTEGER NOT NULL DEFAULT 0,
    target_count    INTEGER NOT NULL DEFAULT 0,
    overlap_share   NUMERIC(5,4) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE graph_cluster_member (
    cluster_id       INTEGER NOT NULL REFERENCES graph_cluster(id) ON DELETE CASCADE,
    phone_number_id  INTEGER NOT NULL REFERENCES phone_number(id) ON DELETE CASCADE,
    PRIMARY KEY (cluster_id, phone_number_id)
);

CREATE TABLE graph_cluster_target (
    cluster_id        INTEGER NOT NULL REFERENCES graph_cluster(id) ON DELETE CASCADE,
    target_number_id  INTEGER NOT NULL REFERENCES phone_number(id) ON DELETE CASCADE,
    PRIMARY KEY (cluster_id, target_number_id)
);

CREATE TABLE graph_cluster_region (
    cluster_id  INTEGER NOT NULL REFERENCES graph_cluster(id) ON DELETE CASCADE,
    region_code VARCHAR(10) NOT NULL,
    PRIMARY KEY (cluster_id, region_code)
);

CREATE TABLE scoring_rule (
    id            SERIAL PRIMARY KEY,
    code          VARCHAR(60)  NOT NULL UNIQUE,
    label         VARCHAR(120) NOT NULL,
    factor_group  VARCHAR(20)  NOT NULL
                  CHECK (factor_group IN ('call','number','graph')),
    description   TEXT,
    base_points   INTEGER      NOT NULL DEFAULT 0,
    weight        NUMERIC(5,2) NOT NULL DEFAULT 1,
    enabled       BOOLEAN      NOT NULL DEFAULT FALSE,
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE blocking_policy (
    id                   SERIAL PRIMARY KEY,
    name                 VARCHAR(120) NOT NULL,
    review_threshold     INTEGER      NOT NULL DEFAULT 40,
    auto_block_threshold INTEGER      NOT NULL DEFAULT 70,
    auto_block_enabled   BOOLEAN      NOT NULL DEFAULT TRUE,
    false_block_cost     INTEGER      NOT NULL DEFAULT 1500,
    missed_fraud_cost    INTEGER      NOT NULL DEFAULT 12000,
    is_active            BOOLEAN      NOT NULL DEFAULT TRUE,
    updated_by           VARCHAR(200),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uq_active_policy
    ON blocking_policy(is_active)
    WHERE is_active = TRUE;

CREATE TABLE call_risk_factor (
    id            BIGSERIAL PRIMARY KEY,
    call_id       BIGINT  NOT NULL REFERENCES call_record(id) ON DELETE CASCADE,
    rule_id       INTEGER NOT NULL REFERENCES scoring_rule(id),
    detail        TEXT,
    points        INTEGER NOT NULL DEFAULT 0,
    UNIQUE (call_id, rule_id)
);

CREATE INDEX idx_call_risk_factor_call ON call_risk_factor(call_id);

CREATE TABLE call_decision (
    call_id       BIGINT PRIMARY KEY
                  REFERENCES call_record(id) ON DELETE CASCADE,
    risk_score    SMALLINT NOT NULL DEFAULT 0 CHECK (risk_score BETWEEN 0 AND 100),
    decision      VARCHAR(20) NOT NULL DEFAULT 'allow'
                  CHECK (decision IN ('allow','review','auto_blocked')),
    computed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    policy_id     INTEGER REFERENCES blocking_policy(id),
    probability DOUBLE PRECISION CONSTRAINT prediction_probability_check CHECK (probability BETWEEN 0 AND 1),
    model_version VARCHAR(64),
    feature_values JSONB
);

CREATE INDEX idx_call_decision_decision ON call_decision(decision);
CREATE INDEX idx_call_decision_score    ON call_decision(risk_score DESC);

CREATE TABLE review_status (
    id    SMALLSERIAL PRIMARY KEY,
    code  VARCHAR(30) NOT NULL UNIQUE,
    label VARCHAR(60) NOT NULL
);

CREATE TABLE call_review (
    call_id           BIGINT PRIMARY KEY
                      REFERENCES call_record(id) ON DELETE CASCADE,
    status_code       VARCHAR(30) NOT NULL DEFAULT 'pending',
    assigned_to       VARCHAR(200),
    reviewed_by       VARCHAR(200),
    review_note       TEXT,
    reviewed_at       TIMESTAMPTZ,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_call_review_status   ON call_review(status_code);
CREATE INDEX idx_call_review_assignee ON call_review(assigned_to);

CREATE TABLE fraud_scenario (
    id    SMALLSERIAL PRIMARY KEY,
    code  VARCHAR(5)  NOT NULL UNIQUE,
    name  VARCHAR(80) NOT NULL,
    description TEXT
);

CREATE TABLE false_positive_label (
    id    SMALLSERIAL PRIMARY KEY,
    code  VARCHAR(5)  NOT NULL UNIQUE,
    name  VARCHAR(80) NOT NULL,
    description TEXT
);

CREATE TABLE phone_number_scenario (
    phone_number_id INTEGER  NOT NULL REFERENCES phone_number(id) ON DELETE CASCADE,
    scenario_id     SMALLINT NOT NULL REFERENCES fraud_scenario(id),
    score           NUMERIC(5,4) NOT NULL DEFAULT 1,
    evidence        TEXT,
    labeled_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (phone_number_id, scenario_id)
);

CREATE TABLE phone_number_false_positive (
    phone_number_id INTEGER  NOT NULL REFERENCES phone_number(id) ON DELETE CASCADE,
    label_id        SMALLINT NOT NULL REFERENCES false_positive_label(id),
    evidence        TEXT,
    labeled_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (phone_number_id, label_id)
);

CREATE TABLE stats_daily (
    day         DATE PRIMARY KEY,
    call_count  INTEGER NOT NULL DEFAULT 0,
    blocked     INTEGER NOT NULL DEFAULT 0,
    review      INTEGER NOT NULL DEFAULT 0,
    allow       INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE stats_counter (
    key         VARCHAR(120) PRIMARY KEY,
    value       BIGINT NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uq_cdr_file_checksum ON cdr_file(checksum);
CREATE UNIQUE INDEX uq_call_record_row_hash ON call_record(row_hash);
CREATE INDEX idx_call_file ON call_record(cdr_file_id);
CREATE INDEX idx_call_caller_started ON call_record(caller_number, started_at);
CREATE INDEX idx_invalid_file ON invalid_cdr_row(cdr_file_id);
CREATE INDEX idx_invalid_code ON invalid_cdr_row(error_code);
CREATE INDEX idx_number_feature_risk ON number_feature(max_risk_score DESC);
CREATE UNIQUE INDEX uq_subscriber_external_id ON subscriber(external_id);
