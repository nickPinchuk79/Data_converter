# Generated by Django 2.0.9 on 2020-05-27 09:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business_register', '0003_auto_20200526_1253'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fop',
            name='hash_code',
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name='historicalfop',
            name='hash_code',
            field=models.CharField(max_length=20),
        ),
    ]
