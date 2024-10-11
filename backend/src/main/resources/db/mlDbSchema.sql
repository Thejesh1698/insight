CREATE TABLE user_article_interactions
(
    id                BIGSERIAL PRIMARY KEY,
    user_id           BIGINT    NOT NULL,
    activity_id       BIGINT    NOT NULL,
    article_id        TEXT      NOT NULL,
    is_article_opened BOOLEAN            DEFAULT FALSE,
    article_position  INTEGER,
    created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    activity_type     TEXT CHECK (activity_type in ('USER_FEED', 'ARTICLES_SEARCH')),
    content_position  JSONB,
    is_summary_read BOOLEAN,
    UNIQUE (user_id, activity_type, activity_id, article_id)
);

CREATE TABLE IF NOT EXISTS user_article_interactions_audit
(
    auditid           BIGSERIAL PRIMARY KEY,
    audittimestamp    TIMESTAMP  NOT NULL DEFAULT NOW(),
    operation         VARCHAR(1) NOT NULL CHECK (operation IN ('S', 'I', 'U', 'D')),
    id                BIGSERIAL,
    user_id           BIGINT,
    activity_id       BIGINT,
    article_id        TEXT,
    is_article_opened BOOLEAN,
    article_position  INTEGER,
    created_at        TIMESTAMP,
    activity_type     TEXT,
    content_position  JSONB,
    is_summary_opened BOOLEAN
);

-- trigger function for user_article_interactions_audit
create or replace function user_article_interactions_audit_proc()
    returns trigger as
$body$
begin
    if (TG_OP = 'INSERT') then
        insert into user_article_interactions_audit
        values (default, now(), 'I', new.*); -- 'I'::operation_type,
    elsif (TG_OP = 'UPDATE') then
        insert into user_article_interactions_audit
        values (default, now(), 'U', new.*); -- 'U'::operation_type,
    elsif (TG_OP = 'DELETE') then
        insert into user_article_interactions_audit
        values (default, now(), 'D', old.*); -- 'D'::operation_type
    end if;
    return null;
end;
$body$ language plpgsql;

-- registering trigger for user_article_interactions_audit_proc
create trigger user_article_interactions_audit_iud_tg
    after insert or update or delete
    on user_article_interactions
    for each row
execute procedure user_article_interactions_audit_proc();


-- for inserting seed data into user_article_interactions_audit
insert into user_article_interactions_audit
(audittimestamp, operation, id, user_id, activity_id, article_id, is_article_opened, article_position, created_at)
select now() as audittimestamp, 'S' as operation, temptable.*
from user_article_interactions as temptable;