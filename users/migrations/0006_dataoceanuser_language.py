# Generated by Django 3.0.7 on 2020-08-07 13:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_remove_candidateusermodel_confirm_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataoceanuser',
            name='language',
            field=models.CharField(blank=True, choices=[('uk', 'Ukrainian'), ('en', 'English')], default='uk', max_length=2, verbose_name='language'),
        ),
    ]
