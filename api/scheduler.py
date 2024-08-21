import logging
import time
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone
from pyrogram import errors

from api.models import (
    PostWatch,
    PostMeasurement,
    Post,
    Notification,
    PublishedPost,
)
from social_networks.tg import TelegramPublisher

scheduler = BackgroundScheduler(settings.SCHEDULER_CONFIG)
DEFAULT_STATS = 0
PURGE_DELTA = timedelta(days=1 << 12)  # disable purge delta
NOTIFICATION_THRESHOLD = 3
POST_SAFE_ZONE_DELTA = timedelta(minutes=5)


def get_previous_stats(post, channel):
    measurements = PostMeasurement.objects.filter(
        post=post, channel=channel
    ).order_by("created_at")
    if not measurements.exists():
        return DEFAULT_STATS
    return measurements.last().views


def _get_unique_watching_channels():
    channels = {}
    for watch in PostWatch.objects.all():
        for channel in watch.post.target_channels.all():
            channels[channel.channel_id] = channel
    return channels


def _purge_old_watches():
    now = timezone.now()
    for watch in PostWatch.objects.filter(created_at__lt=now - PURGE_DELTA):
        watch.delete()


def watch_job():
    _purge_old_watches()
    channels = _get_unique_watching_channels()
    _watch_channels(channels)


def _watch_channels(channels):
    for channel_id, channel in channels.items():
        publications = list(PublishedPost.objects.filter(channel=channel))
        message_ids = list(map(lambda x: x.message_id, publications))
        _watch_channel(channel, channel_id, message_ids, publications)


def force_watch_for_post(post):
    _purge_old_watches()
    _watch_channels({channel.channel_id: channel
                     for channel in post.target_channels.all()})


def _watch_channel(channel, channel_id, message_ids, publications):
    with TelegramPublisher(channel.binding.session_string) as publisher:
        ers, reactions = publisher.get_engagement_rates(channel_id, message_ids)
        views = publisher.get_views_count(channel_id, message_ids)
        for publication in publications:
            _watch_publication(
                channel,
                publication,
                views[publication.message_id],
                ers[publication.message_id],
                reactions[publication.message_id],
            )


def _watch_publication(channel, publication, views, er, reactions):
    measurement = PostMeasurement(
        post=publication.post,
        views=views,
        engagement_rate=er,
        channel=channel,
        reactions=reactions,
    )
    measurement.save()
    previous_value = get_previous_stats(publication.post, channel)
    if (
        previous_value
        < NOTIFICATION_THRESHOLD
        <= views
    ):
        Notification.notify_users(
            publication.post.project.participants,
            f"Your post {publication.post.name} gained "
            f"{views} on channel "
            f"{channel.name}",
        )


def job_send_post(post_id):
    post = Post.objects.get(id=post_id)
    sessions = {}
    for channel in post.target_channels.all():
        key = channel.binding.session_string
        sessions.setdefault(key, [])
        sessions[key].append(channel)

    sent_count = 0

    logging.warning(f"Initializing clients for {post_id} post")

    clients = {}
    for session_string in sessions.keys():
        clients[session_string] = TelegramPublisher(session_string)
        clients[session_string].start()

    delta = (post.schedule_time - timezone.now()).total_seconds() - 1
    logging.warning(f"Waiting for {delta} seconds from {timezone.now().isoformat()}")
    time.sleep(max(0, delta))

    for session_string, channels in sessions.items():
        publisher = clients[session_string]
        for channel in channels:
            logging.warning(f"Sending {post.id} to {channel.channel_id}")
            try:
                message_id = publisher.publish(
                    channel.channel_id,
                    post,
                ).id
                logging.info(f"Sent {post.id}")
            except errors.RPCError as e:
                logging.exception("Failed to sent post")
            else:
                sent_count += 1
                publication = PublishedPost(
                    post=post,
                    channel=channel,
                    message_id=message_id,
                )
                publication.save()
                post_watch = PostWatch(post=post)
                post_watch.save()
                time.sleep(0.1)

    post.is_sent = True
    post.save()

    for client in clients.values():
        client.stop()


def schedule_sending(post_id):
    post = Post.objects.get(id=post_id)
    run_date = post.schedule_time - timedelta(seconds=20)
    if run_date < timezone.now():
        run_date = timezone.now() + timedelta(seconds=1)
    scheduler.add_job(
        job_send_post,
        run_date=run_date,
        args=(post_id,),
        id=f"send_post_{post_id}_job",
        max_instances=1,
        replace_existing=True,
    )


def unschedule_sending(post_id):
    for job in scheduler.get_jobs():
        if job.name == f"send_post_{post_id}_job":
            scheduler.remove_job(job.id)


def is_another_post_scheduled_in_channel_at_that_time(channel,
                                                      post,
                                                      publication_time):
    posts = (Post.objects
             .filter(target_channels=channel)
             .exclude(id=post.id))
    times = filter(lambda x: x is not None,
                   list(map(lambda x: x.schedule_time, list(posts))))
    for schedule in times:
        lb = schedule - POST_SAFE_ZONE_DELTA
        rb = schedule + POST_SAFE_ZONE_DELTA
        print(lb.isoformat(), schedule, rb.isoformat())
        if lb <= publication_time <= rb:
            return True
    return False


def are_any_schedule_clashes(post):
    if not post.schedule_time:
        return False
    return any(map(
        lambda x: is_another_post_scheduled_in_channel_at_that_time(
            x, post, post.schedule_time
        ), post.target_channels.all()
    ))


def start():
    if settings.DEBUG:
        logging.basicConfig()
        logging.getLogger("apscheduler").setLevel(logging.DEBUG)

    scheduler.add_job(
        watch_job,
        trigger=CronTrigger(minute="*/5"),
        id="watch_job",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.start()
