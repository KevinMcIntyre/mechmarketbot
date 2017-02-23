import logging

from telegram.ext import Updater, CommandHandler, Job, Filters
from services.mechmarket import MechMarket
from services.db import DB
from models.user import User

from app.util import write_pid_file, log_exception


def notify(bot, update, args):
    db.record_received_messsage(update.message.from_user['id'], 'notify', update.message.text)
    if len(args) == 0 or not (args[0].startswith('on') or args[0].startswith('off')):
        update.message.reply_text('This command requires an argument of either \'on\' or \'off\'.')
    else:
        user = User(db, update.message.from_user)
        arg_val = get_on_off_or_tags(args)
        if user.notify == arg_val and user.id is not None:
            update.message.reply_text('Setting is already set!')
            return
        user.notify = (arg_val == 'on')
        user.save(db)
        if user.notify:
            update.message.reply_text('You will now receive notifications for posts on /r/mechmarket!')
        else:
            update.message.reply_text('You will no longer receive any notifications.')


def buying(bot, update, args):
    command_handler(bot, update, args, 'buying')


def selling(bot, update, args):
    command_handler(bot, update, args, 'selling')


def group_buy(bot, update, args):
    command_handler(bot, update, args, 'groupbuy')


def vendor(bot, update, args):
    command_handler(bot, update, args, 'vendor')


def artisan(bot, update, args):
    command_handler(bot, update, args, 'artisan')


def tags(bot, update, args):
    db.record_received_messsage(update.message.from_user['id'], 'tags', update.message.text)
    if len(args) == 0:
        update.message.reply_text('This command requires a comma separated argument list')
    else:
        user = User(db, update.message.from_user)
        if user.id is None:
            user.save(db)
        tag_list = separate_tags(' '.join(args))
        tags_set = user.set_tags(db, tag_list)
        if tags_set:
            update.message.reply_text("New tags set to: {}".format(', '.join(tag_list).strip()))
        else:
            update.message.reply_text('An error occurred, please try again.')


def command_handler(bot, update, args, command):
    db.record_received_messsage(update.message.from_user['id'], command, update.message.text)

    user_field_to_update = 'notify_{}'.format(command)

    if len(args) == 0 or not (args[0].startswith('on') or args[0].startswith('off') or args[0].startswith('tags')):
        update.message.reply_text('This command requires an argument of either \'on\', \'off\', or \'tags\'.')
    else:
        user = User(db, update.message.from_user)
        arg_val = get_on_off_or_tags(args)

        if getattr(user, user_field_to_update) == arg_val and user.id is not None:
            update.message.reply_text('Setting is already set!')
            return

        setattr(user, user_field_to_update, arg_val)
        user.save(db)

        if getattr(user, user_field_to_update) == 'on':
            update.message.reply_text('You will now receive all {} notifications.'.format(command))
        elif getattr(user, user_field_to_update) == 'off':
            update.message.reply_text('You will no longer receive {} notifications.'.format(command))
        else:
            update.message.reply_text(
                'You will now only receive {} notifications based on your tags.'.format(command))


def send_notifications_job(bot, job):
    notification_map = get_post_notifications(market)
    transaction = db.connection.begin()

    try:
        for notification in notification_map.values():
            if notification[1] is not None:
                for telegram_id in notification[1]:
                    post = notification[0]['data']
                    message = '{}, {}'.format(post['title'], post['url'])
                    bot.sendMessage(chat_id=telegram_id, text=message)
                    db.record_sent_notification(transaction, telegram_id, market.derive_post_type(post), message,
                                                post['id'])
        transaction.commit()
    except:
        log_exception()
        transaction.rollback()


def get_post_notifications(market):
    try:
        market.refresh_posts()
    except:
        log_exception()
        return dict()
    # Posts are retrieved and stored
    # in a map in order to prevent
    # sending a notification twice
    # in the event a user is identified
    # as having tags that relate to a post
    # in more than one category
    notification_map = dict()
    append_notifications(notification_map, market.get_selling_posts(), "selling")
    append_notifications(notification_map, market.get_buying_posts(), "buying")
    append_notifications(notification_map, market.get_group_buy_posts(), "groupbuy")
    append_notifications(notification_map, market.get_vendor_posts(), "vendor")
    append_notifications(notification_map, market.get_artisan_posts(), "artisan")

    return notification_map


def append_notifications(postmap, posts, post_type):
    # updates the map passed to it
    # key is post.id
    # value is tuple <reddit_post, set_of_telegram_ids>
    for post in posts:
        for telegram_id in db.get_telegram_ids_to_notify(post, post_type):
            if post['data']['id'] not in postmap:
                postmap[post['data']['id']] = (post, {telegram_id})
            else:
                postmap.get(post['data']['id'])[1].add(telegram_id)


def get_on_off_or_tags(args):
    joined = ' '.join(args)
    if joined.startswith('on'):
        return 'on'
    elif joined.startswith('off'):
        return 'off'
    else:
        return 'tags'


def separate_tags(tag_list):
    tags = []
    for tag_string in tag_list.split(','):
        if tag_string.strip():
            tags.append(tag_string.strip())
    return tags


write_pid_file()
logging.basicConfig(filename='bot.log', filemode='w+', format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

db = DB()
market = MechMarket()

updater = Updater('telegram_bot_auth_token')
job_queue = updater.job_queue

updater.dispatcher.add_handler(CommandHandler('notify', notify, pass_args=True))
updater.dispatcher.add_handler(CommandHandler('buying', buying, pass_args=True))
updater.dispatcher.add_handler(CommandHandler('selling', selling, pass_args=True))
updater.dispatcher.add_handler(CommandHandler('groupbuy', group_buy, pass_args=True))
updater.dispatcher.add_handler(CommandHandler('vendor', vendor, pass_args=True))
updater.dispatcher.add_handler(CommandHandler('artisan', artisan, pass_args=True))
updater.dispatcher.add_handler(CommandHandler('tags', tags, pass_args=True))
job_queue.put(Job(send_notifications_job, 60.0), next_t=0.0)

updater.start_polling()
updater.idle()
