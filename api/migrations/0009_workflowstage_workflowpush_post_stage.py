# Generated by Django 5.0.2 on 2024-04-02 13:01

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_usertelegrambinding_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkflowStage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64)),
                ('color', models.CharField(default='00FF00', max_length=6)),
                ('is_end', models.BooleanField()),
                ('next_stage', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.workflowstage')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.project')),
            ],
        ),
        migrations.CreateModel(
            name='WorkflowPush',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pushed_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.post')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.project')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('from_stage', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sources_at', to='api.workflowstage')),
                ('to_stage', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ends_at', to='api.workflowstage')),
            ],
        ),
        migrations.AddField(
            model_name='post',
            name='stage',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.workflowstage'),
        ),
    ]
