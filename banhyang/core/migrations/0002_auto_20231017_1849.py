# Generated by Django 3.0.4 on 2023-10-17 09:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AccountingDetails',
        ),
        migrations.DeleteModel(
            name='AccountingTitle',
        ),
    ]
