import os

from django.conf import settings


def remove_old_photo(photo):
    if photo and photo.name != 'user/photos/default.png':
        old_path = os.path.join(settings.MEDIA_ROOT, 'user/photos/default.png')
        if os.path.exists(old_path):
            os.remove(old_path)