import sqlalchemy


class DB:
    def __init__(self):
        self.engine, self.meta = self.__connect__("postgres", "password", "mechmarketbot_db")
        self.connection = self.engine.connect()

    def __connect__(self, user, password, db, host='localhost', port=5432):
        url = 'postgresql://{}:{}@{}:{}/{}'
        url = url.format(user, password, host, port, db)
        # The return value of create_engine() is our connection object
        engine = sqlalchemy.create_engine(url, client_encoding='utf8')

        # We then bind the connection to MetaData()
        meta = sqlalchemy.MetaData(bind=engine, reflect=True)

        return engine, meta

    def get_telegram_ids_to_notify(self, post, post_type):
        results = self.connection.execute(sqlalchemy.text(
            '''
            SELECT get_users_to_notify_by_tags(:post_type, :post_title) as telegram_id
            UNION
            SELECT u.telegram_id
            FROM users u
            JOIN (
              SELECT
                id  AS user_id,
                CASE
                WHEN :post_type = 'selling'
                  THEN
                CASE WHEN u.notify_selling = 'on'
                  THEN TRUE
                ELSE FALSE
                END
                WHEN :post_type = 'buying'
                  THEN
                CASE WHEN u.notify_buying = 'on'
                  THEN TRUE
                ELSE FALSE
                END
                WHEN :post_type = 'groupbuy'
                  THEN
                CASE WHEN u.notify_groupbuy = 'on'
                  THEN TRUE
                ELSE FALSE
                END
                WHEN :post_type = 'vendor'
                  THEN
                CASE WHEN u.notify_vendor = 'on'
                  THEN TRUE
                ELSE FALSE
                END
                WHEN :post_type = 'artisan'
                  THEN
                CASE WHEN u.notify_artisan = 'on'
                  THEN TRUE
                ELSE FALSE
                END
                ELSE FALSE
                END AS applicable
              FROM users u
            ) applicable ON applicable.user_id = u.id
            AND u.notify = TRUE
            AND applicable.applicable = TRUE;
            '''
        ), {'post_type': post_type, 'post_title': post['data']['title']})

        return map(lambda x: x['telegram_id'], results)

    def record_received_messsage(self, telegram_id, command, message):
        self.connection.execute(
            sqlalchemy.text(
                '''
                INSERT INTO messages_received (telegram_id, command, message)
                VALUES (:telegram_id, :command, :message);
                '''
            ), **{'telegram_id': telegram_id, 'command': command, 'message': message})

    def record_sent_notification(self, transaction, telegram_id, notification_type,
                                 message, reddit_post_id):
        transaction.connection.execute(
            sqlalchemy.text(
                '''
                INSERT INTO notifications_sent (telegram_id, notification_type, message, reddit_post_id)
                VALUES (:telegram_id, :notification_type, :message, :reddit_post_id);
                '''
            ), **{'telegram_id': telegram_id, 'notification_type': notification_type,
                  'message': message, 'reddit_post_id': reddit_post_id})
