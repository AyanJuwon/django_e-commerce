# Generated by Django 3.0.7 on 2020-10-16 12:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_item_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='quantity',
            field=models.PositiveIntegerField(default=1),
            preserve_default=False,
        ),
    ]