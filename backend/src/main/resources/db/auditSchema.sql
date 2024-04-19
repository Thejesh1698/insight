-- AUDIT TABLES

CREATE TABLE IF NOT EXISTS user_articles_search_audit
(
    audit_id            BIGSERIAL PRIMARY KEY,
    audit_timestamp     TIMESTAMP  NOT NULL DEFAULT NOW(),
    operation           VARCHAR(1) NOT NULL CHECK (operation IN ('S', 'I', 'U', 'D')),
    search_id           BIGSERIAL,
    user_id             BIGINT,
    user_inputted_query TEXT,
    cleaned_query       TEXT,
    search_results      TEXT[],
    ml_server_response  JSONB,
    created_at          TIMESTAMP,
    ai_generated_search_summary JSONB
);

-- trigger function for user_articles_search_audit
create or replace function user_articles_search_audit_proc()
    returns trigger as
$body$
begin
    if (TG_OP = 'INSERT') then
        insert into user_articles_search_audit
        values (default, now(), 'I', new.*); -- 'I'::operation_type,
    elsif (TG_OP = 'UPDATE') then
        insert into user_articles_search_audit
        values (default, now(), 'U', new.*); -- 'U'::operation_type,
    elsif (TG_OP = 'DELETE') then
        insert into user_articles_search_audit
        values (default, now(), 'D', old.*); -- 'D'::operation_type
    end if;
    return null;
end;
$body$ language plpgsql;

-- registering trigger for user_articles_search_audit_proc
create trigger user_articles_search_audit_iud_tg
    after insert or update or delete
    on user_articles_search
    for each row
execute procedure user_articles_search_audit_proc();


CREATE TABLE IF NOT EXISTS reactions_audit
(
    audit_id        BIGSERIAL PRIMARY KEY,
    audit_timestamp TIMESTAMP  NOT NULL DEFAULT NOW(),
    operation       VARCHAR(1) NOT NULL CHECK (operation IN ('S', 'I', 'U', 'D')),
    reaction_id     BIGSERIAL,
    reaction        TEXT,
    created_at      TIMESTAMP
);

-- trigger function for reactions_audit
create or replace function reactions_audit_proc()
    returns trigger as
$body$
begin
    if (TG_OP = 'INSERT') then
        insert into reactions_audit
        values (default, now(), 'I', new.*); -- 'I'::operation_type,
    elsif (TG_OP = 'UPDATE') then
        insert into reactions_audit
        values (default, now(), 'U', new.*); -- 'U'::operation_type,
    elsif (TG_OP = 'DELETE') then
        insert into reactions_audit
        values (default, now(), 'D', old.*); -- 'D'::operation_type
    end if;
    return null;
end;
$body$ language plpgsql;

-- registering trigger for reactions_audit_proc
create trigger reactions_audit_iud_tg
    after insert or update or delete
    on reactions
    for each row
execute procedure reactions_audit_proc();


CREATE TABLE IF NOT EXISTS user_article_reactions_audit
(
    audit_id        BIGSERIAL PRIMARY KEY,
    audit_timestamp TIMESTAMP  NOT NULL DEFAULT NOW(),
    operation       VARCHAR(1) NOT NULL CHECK (operation IN ('S', 'I', 'U', 'D')),
    id              BIGINT,
    user_id         BIGINT,
    reaction_id     BIGINT,
    article_id      TEXT,
    created_at      TIMESTAMP
);

-- trigger function for user_article_reactions_audit
create or replace function user_article_reactions_audit_proc()
    returns trigger as
$body$
begin
    if (TG_OP = 'INSERT') then
        insert into user_article_reactions_audit
        values (default, now(), 'I', new.*); -- 'I'::operation_type,
    elsif (TG_OP = 'UPDATE') then
        insert into user_article_reactions_audit
        values (default, now(), 'U', new.*); -- 'U'::operation_type,
    elsif (TG_OP = 'DELETE') then
        insert into user_article_reactions_audit
        values (default, now(), 'D', old.*); -- 'D'::operation_type
    end if;
    return null;
end;
$body$ language plpgsql;

-- registering trigger for user_article_reactions_audit_proc
create trigger user_article_reactions_audit_iud_tg
    after insert or update or delete
    on user_article_reactions
    for each row
execute procedure user_article_reactions_audit_proc();


CREATE TABLE IF NOT EXISTS article_comments_audit
(
    audit_id        BIGSERIAL PRIMARY KEY,
    audit_timestamp TIMESTAMP  NOT NULL DEFAULT NOW(),
    operation       VARCHAR(1) NOT NULL CHECK (operation IN ('S', 'I', 'U', 'D')),
    comment_id      BIGINT,
    user_id         BIGINT,
    article_id      TEXT,
    comment_text    TEXT,
    created_at      TIMESTAMP
);

-- trigger function for article_comments_audit
create or replace function article_comments_audit_proc()
    returns trigger as
$body$
begin
    if (TG_OP = 'INSERT') then
        insert into article_comments_audit
        values (default, now(), 'I', new.*); -- 'I'::operation_type,
    elsif (TG_OP = 'UPDATE') then
        insert into article_comments_audit
        values (default, now(), 'U', new.*); -- 'U'::operation_type,
    elsif (TG_OP = 'DELETE') then
        insert into article_comments_audit
        values (default, now(), 'D', old.*); -- 'D'::operation_type
    end if;
    return null;
end;
$body$ language plpgsql;

-- registering trigger for article_comments_audit_proc
create trigger article_comments_audit_iud_tg
    after insert or update or delete
    on article_comments
    for each row
execute procedure article_comments_audit_proc();

----------------------------------------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_article_bookmarks_audit
(
    audit_id        BIGSERIAL PRIMARY KEY,
    audit_timestamp TIMESTAMP  NOT NULL DEFAULT NOW(),
    operation       VARCHAR(1) NOT NULL CHECK (operation IN ('S', 'I', 'U', 'D')),
    bookmark_id      BIGINT,
    user_id         BIGINT,
    article_id      TEXT,
    created_at      TIMESTAMP
);

-- trigger function for user_article_bookmarks_audit
create or replace function user_article_bookmarks_audit_proc()
    returns trigger as
$body$
begin
    if (TG_OP = 'INSERT') then
        insert into user_article_bookmarks_audit
        values (default, now(), 'I', new.*); -- 'I'::operation_type,
    elsif (TG_OP = 'UPDATE') then
        insert into user_article_bookmarks_audit
        values (default, now(), 'U', new.*); -- 'U'::operation_type,
    elsif (TG_OP = 'DELETE') then
        insert into user_article_bookmarks_audit
        values (default, now(), 'D', old.*); -- 'D'::operation_type
    end if;
    return null;
end;
$body$ language plpgsql;

-- registering trigger for user_article_bookmarks_audit_proc
create trigger user_article_bookmarks_audit_iud_tg
    after insert or update or delete
    on user_article_bookmarks
    for each row
execute procedure user_article_bookmarks_audit_proc();

----------------------------------------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_article_reading_history_audit
(
    audit_id        BIGSERIAL PRIMARY KEY,
    audit_timestamp TIMESTAMP  NOT NULL DEFAULT NOW(),
    operation       VARCHAR(1) NOT NULL CHECK (operation IN ('S', 'I', 'U', 'D')),
    bookmark_id      BIGINT,
    user_id         BIGINT,
    article_id      TEXT,
    created_at      TIMESTAMP
);

-- trigger function for user_article_reading_history_audit
create or replace function user_article_reading_history_audit_proc()
    returns trigger as
$body$
begin
    if (TG_OP = 'INSERT') then
        insert into user_article_reading_history_audit
        values (default, now(), 'I', new.*); -- 'I'::operation_type,
    elsif (TG_OP = 'UPDATE') then
        insert into user_article_reading_history_audit
        values (default, now(), 'U', new.*); -- 'U'::operation_type,
    elsif (TG_OP = 'DELETE') then
        insert into user_article_reading_history_audit
        values (default, now(), 'D', old.*); -- 'D'::operation_type
    end if;
    return null;
end;
$body$ language plpgsql;

-- registering trigger for user_article_reading_history_audit_proc
create trigger user_article_reading_history_audit_iud_tg
    after insert or update or delete
    on user_article_reading_history
    for each row
execute procedure user_article_reading_history_audit_proc();

----------------------------------------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_reported_content_audit
(
    audit_id        BIGSERIAL PRIMARY KEY,
    audit_timestamp TIMESTAMP  NOT NULL DEFAULT NOW(),
    operation       VARCHAR(1) NOT NULL CHECK (operation IN ('S', 'I', 'U', 'D')),
    report_id       BIGINT,
    user_id         BIGINT,
    content_id      TEXT,
    content_type    TEXT CHECK (content_type in ('ARTICLE', 'PODCAST', 'PODCAST_EPISODE')) NOT NULL DEFAULT 'ARTICLE',
    reason_id       INT,
    created_at      TIMESTAMP
);

-- trigger function for user_reported_content_audit
CREATE OR REPLACE FUNCTION user_reported_content_audit_proc()
    RETURNS TRIGGER AS
$BODY$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO user_reported_content_audit (audit_timestamp, operation, report_id, user_id, content_id, content_type, reason_id, created_at)
        VALUES (NOW(), 'I', NEW.report_id, NEW.user_id, NEW.content_id, NEW.content_type, NEW.reason_id, NEW.created_at);
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO user_reported_content_audit (audit_timestamp, operation, report_id, user_id, content_id, content_type, reason_id, created_at)
        VALUES (NOW(), 'U', OLD.report_id, OLD.user_id, OLD.content_id, OLD.content_type, OLD.reason_id, OLD.created_at);
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO user_reported_content_audit (audit_timestamp, operation, report_id, user_id, content_id, content_type, reason_id, created_at)
        VALUES (NOW(), 'D', OLD.report_id, OLD.user_id, OLD.content_id, OLD.content_type, OLD.reason_id, OLD.created_at);
    END IF;
    RETURN NULL;
END;
$BODY$
LANGUAGE plpgsql;

-- Registering trigger for user_reported_content_audit_proc
CREATE TRIGGER user_reported_content_audit_iud_tg
AFTER INSERT OR UPDATE OR DELETE
ON user_reported_content
FOR EACH ROW
EXECUTE PROCEDURE user_reported_content_audit_proc();

----------------------------------------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_content_preferences_audit
(
    audit_id        BIGSERIAL  PRIMARY KEY,
    audit_timestamp TIMESTAMP  NOT NULL DEFAULT NOW(),
    operation       VARCHAR(1) NOT NULL CHECK (operation IN ('S', 'I', 'U', 'D')),
    preference_id   BIGINT,
    user_id         BIGINT,
    content_id      TEXT,
    content_type    TEXT  NOT NULL,
    preference_type TEXT  NOT NULL,
    created_at      TIMESTAMP
);

-- trigger function for user_content_preferences_audit
CREATE OR REPLACE FUNCTION user_content_preferences_audit_proc()
    RETURNS TRIGGER AS
$BODY$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO user_content_preferences_audit (audit_timestamp, operation, preference_id, user_id, content_id, content_type, preference_type, created_at)
        VALUES (NOW(), 'I', NEW.preference_id, NEW.user_id, NEW.content_id, NEW.content_type, NEW.preference_type, NEW.created_at);
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO user_content_preferences_audit (audit_timestamp, operation, preference_id, user_id, content_id, content_type, preference_type, created_at)
        VALUES (NOW(), 'U', OLD.preference_id, OLD.user_id, OLD.content_id, OLD.content_type, OLD.preference_type, OLD.created_at);
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO user_content_preferences_audit (audit_timestamp, operation, preference_id, user_id, content_id, content_type, preference_type, created_at)
        VALUES (NOW(), 'D', OLD.preference_id, OLD.user_id, OLD.content_id, OLD.content_type, OLD.preference_type, OLD.created_at);
    END IF;
    RETURN NULL;
END;
$BODY$
LANGUAGE plpgsql;

-- Registering trigger for user_content_preferences_audit_proc
CREATE TRIGGER user_content_preferences_audit_iud_tg
AFTER INSERT OR UPDATE OR DELETE
ON user_content_preferences
FOR EACH ROW
EXECUTE PROCEDURE user_content_preferences_audit_proc();
