# Generated by Django 5.0.2 on 2024-04-02 22:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0011_fileuploadedtotelegram"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fileuploadedtotelegram",
            name="chat_id",
            field=models.BigIntegerField(),
        ),
    ]
