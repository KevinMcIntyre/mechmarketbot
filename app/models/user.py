import sqlalchemy
from datetime import datetime, timezone

from app.util import log_exception


class User:
    def __init__(self, db, telegram_info):
        info = telegram_info.__dict__
        info['id'] = str(telegram_info.id)

        result = db.connection.execute(sqlalchemy.text(
            '''
                SELECT * FROM users WHERE telegram_id = :id;
            '''), **info)

        rows = result.fetchall()

        if not len(rows):
            self.id = None
            self.telegram_id = telegram_info['id']
            self.first_name = telegram_info['first_name']
            self.last_name = telegram_info['last_name']
            self.username = telegram_info['username']
            self.notify = True
            self.notify_buying = 'on'
            self.notify_selling = 'on'
            self.notify_groupbuy = 'on'
            self.notify_vendor = 'on'
            self.notify_artisan = 'on'
        else:
            row = rows[0]
            self.id = row['id']
            self.telegram_id = row['telegram_id']
            self.first_name = row['first_name']
            self.last_name = row['last_name']
            self.username = row['username']
            self.notify = row['notify']
            self.notify_buying = row['notify_buying']
            self.notify_selling = row['notify_selling']
            self.notify_groupbuy = row['notify_groupbuy']
            self.notify_vendor = row['notify_vendor']
            self.notify_artisan = row['notify_artisan']

    def save(self, db):
        params = self.__dict__
        if self.id is None:
            result = db.connection.execute(sqlalchemy.text(
                '''
                    INSERT INTO users
                    (telegram_id, first_name, last_name, username,
                    notify, notify_buying, notify_selling, notify_groupbuy,
                    notify_vendor, notify_artisan)
                    VALUES
                      (:telegram_id, :first_name, :last_name,
                      :username, :notify, :notify_buying, :notify_selling,
                      :notify_groupbuy, :notify_vendor, :notify_artisan) RETURNING id;
                '''
            ), **params)
            rows = result.fetchall()
            self.id = rows[0]['id']
        else:
            params['modified_date'] = datetime.now(timezone.utc)
            db.connection.execute(sqlalchemy.text(
                '''
                    UPDATE users
                    SET first_name = :first_name,
                        last_name = :last_name,
                        username = :username,
                        notify = :notify,
                        notify_buying = :notify_buying,
                        notify_selling = :notify_selling,
                        notify_groupbuy = :notify_groupbuy,
                        notify_vendor = :notify_vendor,
                        notify_artisan = :notify_artisan,
                        modified_date = :modified_date
                    WHERE telegram_id = :telegram_id;
                '''
            ), **params)

    def set_tags(self, db, tags):
        # Set previous tags for user to not current
        db.connection.execute(sqlalchemy.text(
            '''
                UPDATE tags
                SET is_current = FALSE,
                    modified_date = :modified_date
                WHERE user_id = :user_id AND is_current = TRUE;
            '''
        ), **{'user_id': self.id, 'modified_date': datetime.now(timezone.utc)})
        # Save each new tag to database in a transaction
        transaction = db.connection.begin()
        try:
            for tag in tags:
                db.connection.execute(sqlalchemy.text(
                    '''
                        INSERT INTO tags(user_id, tag, is_current)
                        VALUES (:user_id, :tag, TRUE);
                    '''
                ), **{'user_id': self.id, 'tag': tag})
            transaction.commit()
            return True
        except:
            log_exception()
            transaction.rollback()
            return False
