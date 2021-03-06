# Generated by Django 3.0.7 on 2020-06-26 10:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business_register', '0015_historicalfounderfull'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exchangedatafop',
            name='end_number',
            field=models.CharField(max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='exchangedatafop',
            name='start_number',
            field=models.CharField(max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='fop',
            name='contact_info',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='fop',
            name='estate_manager',
            field=models.CharField(max_length=125, null=True),
        ),
        migrations.AlterField(
            model_name='fop',
            name='hash_code',
            field=models.CharField(db_index=True, max_length=600),
        ),
        migrations.AlterField(
            model_name='fop',
            name='termination_cancel_info',
            field=models.CharField(max_length=275, null=True),
        ),
        migrations.AlterField(
            model_name='fop',
            name='vp_dates',
            field=models.CharField(max_length=140, null=True),
        ),
        migrations.AlterField(
            model_name='historicalfop',
            name='contact_info',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='historicalfop',
            name='estate_manager',
            field=models.CharField(max_length=125, null=True),
        ),
        migrations.AlterField(
            model_name='historicalfop',
            name='hash_code',
            field=models.CharField(db_index=True, max_length=600),
        ),
        migrations.AlterField(
            model_name='historicalfop',
            name='termination_cancel_info',
            field=models.CharField(max_length=275, null=True),
        ),
        migrations.AlterField(
            model_name='historicalfop',
            name='vp_dates',
            field=models.CharField(max_length=140, null=True),
        ),
    ]
