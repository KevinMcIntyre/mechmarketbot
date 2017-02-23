CREATE TYPE command AS ENUM ('notify', 'tags', 'selling', 'buying', 'trading', 'groupbuy', 'vendor', 'interestcheck', 'artisan', 'sold', 'purchased', 'meta');

CREATE TYPE notification_setting AS ENUM ('on', 'off', 'tags');

CREATE TABLE users (
  id              BIGSERIAL PRIMARY KEY                      NOT NULL,
  telegram_id     VARCHAR(15) UNIQUE                         NOT NULL,
  first_name      VARCHAR(255),
  last_name       VARCHAR(255),
  username        VARCHAR(255),
  notify          BOOLEAN                                    NOT NULL,
  notify_buying   notification_setting                       NOT NULL,
  notify_selling  notification_setting                       NOT NULL,
  notify_groupbuy notification_setting                       NOT NULL,
  notify_vendor   notification_setting                       NOT NULL,
  notify_artisan  notification_setting                       NOT NULL,
  creation_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP        NOT NULL,
  modified_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP        NOT NULL
);

CREATE TABLE tags (
  id            BIGSERIAL PRIMARY KEY                      NOT NULL,
  tag           VARCHAR(20)                                NOT NULL,
  user_id       BIGINT                                     NOT NULL  REFERENCES users (id),
  is_current    BOOLEAN                                    NOT NULL,
  creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP        NOT NULL,
  modified_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP        NOT NULL
);

CREATE TABLE messages_received (
  id            BIGSERIAL PRIMARY KEY                      NOT NULL,
  telegram_id   VARCHAR(15)                                NOT NULL,
  command       command                                    NOT NULL,
  message       TEXT                                       NOT NULL,
  creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP        NOT NULL
);

CREATE TABLE notifications_sent (
  id                BIGSERIAL PRIMARY KEY                      NOT NULL,
  telegram_id       VARCHAR(15)                                NOT NULL REFERENCES users (telegram_id),
  notification_type command                                    NOT NULL,
  message           TEXT                                       NOT NULL,
  reddit_post_id    VARCHAR(20),
  creation_date     TIMESTAMP DEFAULT CURRENT_TIMESTAMP        NOT NULL
);

CREATE OR REPLACE FUNCTION get_users_to_notify_by_tags(post_type VARCHAR(25), post_title TEXT)
  RETURNS SETOF VARCHAR(15) AS $$
DECLARE
  tag_row  RECORD;
  user_row RECORD;
BEGIN
  FOR tag_row IN SELECT DISTINCT ON (UPPER(tag)) tag
                 FROM tags
                 WHERE tags.is_current = TRUE
  LOOP
    CASE WHEN (SELECT to_tsvector(post_title) @@ plainto_tsquery(tag_row.tag))
      THEN
        FOR user_row IN
        (SELECT u.*
         FROM users u
           JOIN tags t ON t.user_id = u.id
           JOIN (
                  SELECT
                    id  AS user_id,
                    CASE
                    WHEN post_type = 'selling'
                      THEN
                        CASE WHEN u.notify_selling = 'tags'
                          THEN TRUE
                        ELSE FALSE
                        END
                    WHEN post_type = 'buying'
                      THEN
                        CASE WHEN u.notify_buying = 'tags'
                          THEN TRUE
                        ELSE FALSE
                        END
                    WHEN post_type = 'groupbuy'
                      THEN
                        CASE WHEN u.notify_groupbuy = 'tags'
                          THEN TRUE
                        ELSE FALSE
                        END
                    WHEN post_type = 'vendor'
                      THEN
                        CASE WHEN u.notify_vendor = 'tags'
                          THEN TRUE
                        ELSE FALSE
                        END
                    WHEN post_type = 'artisan'
                      THEN
                        CASE WHEN u.notify_artisan = 'tags'
                          THEN TRUE
                        ELSE FALSE
                        END
                    ELSE FALSE
                    END AS applicable
                  FROM users u
                ) applicable ON applicable.user_id = u.id
         WHERE UPPER(t.tag) = UPPER(tag_row.tag)
               AND u.notify = TRUE
               AND applicable.applicable = TRUE)
        LOOP
          RETURN QUERY VALUES (user_row.telegram_id);
        END LOOP;
    ELSE
      CONTINUE;
    END CASE;
  END LOOP;
END;
$$
LANGUAGE plpgsql;