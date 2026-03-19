from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
import logging

from .models import User


logger = logging.getLogger(__name__)


def _safe_delete(storage, file_name):
    """Best-effort file delete to avoid failing user updates on Windows locks."""
    if not file_name:
        return
    try:
        storage.delete(file_name)
    except FileNotFoundError:
        # Already deleted by another path/process.
        return
    except PermissionError:
        logger.warning("Could not delete locked profile image file: %s", file_name)
    except OSError as exc:
        logger.warning("Could not delete profile image file %s: %s", file_name, exc)


@receiver(pre_save, sender=User)
def delete_replaced_profile_picture(sender, instance, **kwargs):
    """Remove old profile picture file when user uploads a new one."""
    if not instance.pk:
        return

    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    old_file = previous.profile_picture
    new_file = instance.profile_picture

    if old_file and old_file.name and old_file != new_file:
        _safe_delete(old_file.storage, old_file.name)


@receiver(post_delete, sender=User)
def delete_profile_picture_on_user_delete(sender, instance, **kwargs):
    """Remove profile picture file from storage when user is deleted."""
    if instance.profile_picture and instance.profile_picture.name:
        _safe_delete(instance.profile_picture.storage, instance.profile_picture.name)
