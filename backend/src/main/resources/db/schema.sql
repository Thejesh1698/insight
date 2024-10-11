CREATE TABLE users
(
    user_id            BIGSERIAL PRIMARY KEY,
    user_mobile_number TEXT UNIQUE,
    user_name          TEXT,
    created_at         TIMESTAMP DEFAULT now(),
    user_email         TEXT UNIQUE
);

CREATE TABLE topics
(
    topic_id   BIGSERIAL PRIMARY KEY,
    topic_name TEXT UNIQUE NOT NULL,
    category   TEXT,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE (topic_name, category)
);

CREATE TABLE user_topic_interests
(
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT REFERENCES users (user_id)   NOT NULL,
    topic_id   BIGINT REFERENCES topics (topic_id) NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE (user_id, topic_id)
);

CREATE TABLE user_auth_tokens
(
    auth_token_id BIGSERIAL PRIMARY KEY,
    user_id       BIGINT REFERENCES users (user_id),
    auth_token    TEXT UNIQUE NOT NULL,
    ttl           BIGINT      NOT NULL,
    created_at    TIMESTAMP   NOT NULL DEFAULT now()
);


CREATE TABLE feed_sessions
(
    session_id BIGSERIAL PRIMARY KEY,
    user_id    BIGINT REFERENCES users (user_id)                                   NOT NULL,
    created_at TIMESTAMP                                                                    DEFAULT now(),
    feed_type  TEXT CHECK (feed_type in ('ARTICLE', 'PODCAST', 'PODCAST_EPISODE')) NOT NULL DEFAULT 'ARTICLE',
    UNIQUE (user_id, session_id)
);

CREATE TABLE feed_details
(
    feed_id            BIGSERIAL PRIMARY KEY,
    session_id         BIGINT REFERENCES feed_sessions (session_id) NOT NULL,
    articles           TEXT[]                                       NOT NULL,
    ml_server_response JSONB,
    created_at         TIMESTAMP DEFAULT now(),
    UNIQUE (feed_id, session_id)
);

CREATE TABLE user_articles_search
(
    search_id                   BIGSERIAL PRIMARY KEY,
    user_id                     BIGINT REFERENCES users (user_id) NOT NULL,
    user_inputted_query         TEXT                              NOT NULL,
    cleaned_query               TEXT                              NOT NULL,
    search_results              TEXT[]                            NOT NULL,
    ml_server_response          JSONB                             NOT NULL,
    ai_generated_search_summary JSONB,
    created_at                  TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now())
);

CREATE TABLE reactions
(
    reaction_id BIGSERIAL PRIMARY KEY,
    reaction    TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now())
);

CREATE TABLE user_article_reactions
(
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users (user_id)         NOT NULL,
    reaction_id BIGINT REFERENCES reactions (reaction_id) NOT NULL,
    article_id  TEXT                                      NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now()),
    UNIQUE (user_id, article_id)
);

CREATE TABLE article_comments
(
    comment_id   BIGSERIAL PRIMARY KEY,
    user_id      BIGINT REFERENCES users (user_id) NOT NULL,
    article_id   TEXT                              NOT NULL,
    comment_text TEXT                              NOT NULL,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now())
);

CREATE TABLE user_article_bookmarks
(
    bookmark_id BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users (user_id) NOT NULL,
    article_id  TEXT                              NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now()),
    UNIQUE (user_id, article_id)
);

CREATE TABLE user_article_reading_history
(
    history_id BIGSERIAL PRIMARY KEY,
    user_id    BIGINT REFERENCES users (user_id) NOT NULL,
    article_id TEXT                              NOT NULL,
    read_at    TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now())
);

CREATE TABLE user_content_preferences
(
    preference_id   BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users (user_id) ON DELETE CASCADE NOT NULL,
    content_id      TEXT                                                NOT NULL,
    content_type    TEXT                                                NOT NULL,
    preference_type TEXT                                                NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now()),
    UNIQUE (user_id, content_id, preference_type)
);

CREATE TABLE report_reasons
(
    id     SERIAL PRIMARY KEY,
    reason VARCHAR(255) NOT NULL
);

CREATE TABLE user_reported_content
(
    report_id    BIGSERIAL PRIMARY KEY,
    user_id      BIGINT REFERENCES users (user_id) ON DELETE CASCADE                    NOT NULL,
    content_id   TEXT                                                                   NOT NULL,
    reason_id    INT REFERENCES report_reasons (id) ON DELETE CASCADE                   NOT NULL,
    details      TEXT,
    content_type TEXT CHECK (content_type in ('ARTICLE', 'PODCAST', 'PODCAST_EPISODE')) NOT NULL DEFAULT 'ARTICLE',
    created_at   TIMESTAMP WITH TIME ZONE                                                        DEFAULT timezone('UTC'::text, now())
);

CREATE TABLE user_investment_options
(
    investment_option_id BIGSERIAL PRIMARY KEY,
    name                 TEXT NOT NULL,
    nse_ticker           TEXT UNIQUE,
    bse_ticker           TEXT UNIQUE,
    active               BOOLEAN                  NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now())
);

CREATE TABLE user_smallcase_transactions
(
    id                       BIGSERIAL PRIMARY KEY,
    user_id                  BIGINT REFERENCES users (user_id) ON DELETE CASCADE                       NOT NULL,
    smallcase_transaction_id TEXT UNIQUE                                                               NOT NULL,
    transaction_type         TEXT CHECK (transaction_type in ('HOLDINGS_IMPORT'))                      NOT NULL DEFAULT 'HOLDINGS_IMPORT',
    transaction_status       TEXT CHECK (transaction_status in ('STARTED', 'AUTHORIZED', 'COMPLETED')) NOT NULL DEFAULT 'STARTED',
    expire_at                BIGINT                                                                    NOT NULL,
    vendor_response          JSONB,
    broker                   TEXT CHECK (broker in
                                         ('FIVE_PAISA', 'ANGEL_BROKING', 'DHAN', 'FISDOM', 'GROWW', 'IIFL', 'MOTILAL',
                                          'TRUSTLINE', 'UPSTOX', 'KITE')),
    last_updated             TIMESTAMP WITH TIME ZONE                                                           DEFAULT timezone('UTC'::text, now()),
    vendor_webhook_response  JSONB                                                                              DEFAULT NULL,
    created_at               TIMESTAMP WITH TIME ZONE                                                           DEFAULT timezone('UTC'::text, now())
);

CREATE TABLE user_investments
(
    investment_id              BIGSERIAL PRIMARY KEY,
    user_id                    BIGINT REFERENCES users (user_id) ON DELETE CASCADE                                NOT NULL,
    investment_option_id       BIGINT REFERENCES user_investment_options (investment_option_id) ON DELETE CASCADE NOT NULL,
    small_case_transaction_ref BIGINT REFERENCES user_smallcase_transactions (id) ON DELETE CASCADE               NOT NULL,
    quantity                   INT                                                                                NOT NULL,
    average_price              NUMERIC                                                                            NOT NULL,
    broker                     TEXT CHECK (broker in
                                           ('FIVE_PAISA', 'ANGEL_BROKING', 'DHAN', 'FISDOM', 'GROWW', 'IIFL', 'MOTILAL',
                                            'TRUSTLINE', 'UPSTOX', 'KITE')),
    created_at                 TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now()),
    UNIQUE (user_id, investment_option_id, broker)
);

CREATE TABLE user_smallcase_broker_auth_tokens
(
    id                   BIGSERIAL PRIMARY KEY,
    user_id              BIGINT REFERENCES users (user_id) ON DELETE CASCADE NOT NULL,
    smallcase_auth_token TEXT UNIQUE                                         NOT NULL,
    broker               TEXT CHECK (broker in
                                     ('FIVE_PAISA', 'ANGEL_BROKING', 'DHAN', 'FISDOM', 'GROWW', 'IIFL', 'MOTILAL',
                                      'TRUSTLINE', 'UPSTOX', 'KITE'))        NOT NULL,
    created_at           TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now()),
    UNIQUE (user_id, broker)
);

CREATE TABLE investment_option_kite_trading_symbol_mapping
(
    id                   BIGSERIAL PRIMARY KEY,
    investment_option_id BIGINT REFERENCES user_investment_options (investment_option_id) ON DELETE CASCADE NOT NULL,
    exchange             TEXT CHECK (exchange in ('NSE', 'BSE'))                                            NOT NULL,
    kite_trading_symbol  TEXT                                                                               NOT NULL,
    instrument_token     TEXT                                                                        NOT NULL,
    last_updated         TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now()),
    created_at           TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now()),
    UNIQUE (investment_option_id, exchange),
    UNIQUE (kite_trading_symbol, exchange)
);

CREATE TABLE investment_option_historic_price
(
    id                   BIGSERIAL PRIMARY KEY,
    investment_option_id BIGINT REFERENCES user_investment_options (investment_option_id) ON DELETE CASCADE NOT NULL,
    open                 NUMERIC                                                                            NOT NULL,
    high                 NUMERIC                                                                            NOT NULL,
    low                  NUMERIC                                                                            NOT NULL,
    close                NUMERIC                                                                            NOT NULL,
    volume               NUMERIC                                                                            NOT NULL,
    price_date           DATE                                                                                        DEFAULT now(),
    exchange             TEXT CHECK (exchange in ('NSE', 'BSE'))                                            NOT NULL DEFAULT 'NSE',
    created_at           TIMESTAMP WITH TIME ZONE                                                                    DEFAULT timezone('UTC'::text, now()),
    UNIQUE (investment_option_id, exchange, price_date)
);


CREATE TABLE investment_option_price
(
    id                   BIGSERIAL PRIMARY KEY,
    investment_option_id BIGINT REFERENCES user_investment_options (investment_option_id) ON DELETE CASCADE NOT NULL,
    open                 NUMERIC                                                                            NOT NULL,
    high                 NUMERIC                                                                            NOT NULL,
    low                  NUMERIC                                                                            NOT NULL,
    close                NUMERIC                                                                            NOT NULL,
    volume               NUMERIC                                                                            NOT NULL,
    price_time           TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now()),
    exchange             TEXT CHECK (exchange in ('NSE', 'BSE'))                                            NOT NULL,
    created_at           TIMESTAMP WITH TIME ZONE DEFAULT timezone('UTC'::text, now()),
    UNIQUE (investment_option_id, exchange, price_time)
);