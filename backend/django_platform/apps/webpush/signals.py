from django.conf import settings
from django.contrib.auth.signals import user_logged_out
from django.db import transaction
from django.db.models import Max
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from apps.communications.models import Event
from apps.content.models import Article
from .models import PushNotification, PushSubscription


@receiver(pre_save, sender=Article, dispatch_uid="webpush_article_before")
@receiver(pre_save, sender=Event, dispatch_uid="webpush_event_before")
def before_publication(sender, instance, raw=False, **kwargs):
    if raw or not settings.WEBPUSH_ENABLED:
        return
    fields = ["status"] if sender is Article else ["is_published", "is_cancelled"]
    previous = sender.objects.filter(pk=instance.pk).values(*fields).first() if instance.pk else None
    instance._push_previously_published = bool(previous and (
        previous["status"] == "published" if sender is Article else previous["is_published"] and not previous["is_cancelled"]
    ))


@receiver(post_save, sender=Article, dispatch_uid="webpush_article_after")
@receiver(post_save, sender=Event, dispatch_uid="webpush_event_after")
def after_publication(sender, instance, raw=False, **kwargs):
    if raw or not settings.WEBPUSH_ENABLED:
        return
    update_fields = kwargs.get("update_fields")
    publication_fields = {"status"} if sender is Article else {"is_published", "is_cancelled"}
    if update_fields is not None and publication_fields.isdisjoint(update_fields):
        return
    published = instance.status == "published" if sender is Article else instance.is_published and not instance.is_cancelled
    if not published or getattr(instance, "_push_previously_published", True):
        return
    kind, identifier = ("article" if sender is Article else "event"), instance.pk

    def enqueue():
        # Only a queue record is written here; fan-out and HTTP happen in cron.
        maximum = PushSubscription.objects.aggregate(value=Max("pk"))["value"] or 0
        PushNotification.objects.get_or_create(kind=kind, object_id=identifier, defaults={"max_subscription_id": maximum})

    transaction.on_commit(enqueue)


@receiver(user_logged_out, dispatch_uid="webpush_logout")
def detach_logout(sender, request, **kwargs):
    if request and request.session.session_key:
        PushSubscription.objects.filter(session_key=request.session.session_key).update(user=None, session_key="")
