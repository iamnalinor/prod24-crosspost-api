from django.contrib import admin
from django.contrib.auth.models import AbstractUser
from django.db.models import Model

from . import models

for name in dir(models):
    model = getattr(models, name)
    if (
        isinstance(model, type)
        and issubclass(model, Model)
        and model is not AbstractUser
    ):
        admin.site.register(model)
