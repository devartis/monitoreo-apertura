# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-06-09 15:50
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('red_nodos', '0002_auto_20170609_1117'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tablecolumn',
            name='indicator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dashboard.IndicatorType'),
        ),
    ]
