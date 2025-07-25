# Generated by Django 5.1.5 on 2025-02-23 11:26
from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExampleFFK",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ExampleFMTM",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ExampleFOTO",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="NestedExampleFFK",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="NestedExampleFMTM",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="NestedExampleFOTO",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Example",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("symmetrical_field", models.ManyToManyField(to="example.example")),
                (
                    "example_ffk",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_set",
                        to="example.exampleffk",
                    ),
                ),
                (
                    "example_fmtm_set",
                    models.ManyToManyField(related_name="example_set", to="example.examplefmtm"),
                ),
                (
                    "example_foto",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example",
                        to="example.examplefoto",
                    ),
                ),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="examplefoto",
            name="example_ffk",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="example_foto_set",
                to="example.nestedexampleffk",
            ),
        ),
        migrations.AddField(
            model_name="examplefmtm",
            name="example_ffk",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="example_fmtm_set",
                to="example.nestedexampleffk",
            ),
        ),
        migrations.AddField(
            model_name="exampleffk",
            name="example_ffk",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="example_ffk_set",
                to="example.nestedexampleffk",
            ),
        ),
        migrations.AddField(
            model_name="examplefoto",
            name="example_fmtm_set",
            field=models.ManyToManyField(related_name="example_foto_set", to="example.nestedexamplefmtm"),
        ),
        migrations.AddField(
            model_name="examplefmtm",
            name="example_fmtm_set",
            field=models.ManyToManyField(related_name="example_fmtm_set", to="example.nestedexamplefmtm"),
        ),
        migrations.AddField(
            model_name="exampleffk",
            name="example_fmtm_set",
            field=models.ManyToManyField(related_name="example_ffk_set", to="example.nestedexamplefmtm"),
        ),
        migrations.CreateModel(
            name="ExampleROTO",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "example",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_roto",
                        to="example.example",
                    ),
                ),
                (
                    "example_ffk",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_roto_set",
                        to="example.nestedexampleffk",
                    ),
                ),
                (
                    "example_fmtm_set",
                    models.ManyToManyField(related_name="example_roto_set", to="example.nestedexamplefmtm"),
                ),
                (
                    "example_foto",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_roto",
                        to="example.nestedexamplefoto",
                    ),
                ),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ExampleRMTM",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "examples",
                    models.ManyToManyField(related_name="example_rmtm_set", to="example.example"),
                ),
                (
                    "example_ffk",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_rmtm_set",
                        to="example.nestedexampleffk",
                    ),
                ),
                (
                    "example_fmtm_set",
                    models.ManyToManyField(related_name="example_rmtm_set", to="example.nestedexamplefmtm"),
                ),
                (
                    "example_foto",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_rmtm",
                        to="example.nestedexamplefoto",
                    ),
                ),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ExampleRFK",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "example",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_rfk_set",
                        to="example.example",
                    ),
                ),
                (
                    "example_ffk",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_rfk_set",
                        to="example.nestedexampleffk",
                    ),
                ),
                (
                    "example_fmtm_set",
                    models.ManyToManyField(related_name="example_rfk_set", to="example.nestedexamplefmtm"),
                ),
                (
                    "example_foto",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_rfk",
                        to="example.nestedexamplefoto",
                    ),
                ),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="examplefoto",
            name="example_foto",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="example_foto",
                to="example.nestedexamplefoto",
            ),
        ),
        migrations.AddField(
            model_name="examplefmtm",
            name="example_foto",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="example_fmtm",
                to="example.nestedexamplefoto",
            ),
        ),
        migrations.AddField(
            model_name="exampleffk",
            name="example_foto",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="example_ffk",
                to="example.nestedexamplefoto",
            ),
        ),
        migrations.CreateModel(
            name="NestedExampleRFK",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "example_ffk",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_rfk_set",
                        to="example.exampleffk",
                    ),
                ),
                (
                    "example_fmtm",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_rfk_set",
                        to="example.examplefmtm",
                    ),
                ),
                (
                    "example_foto",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_rfk_set",
                        to="example.examplefoto",
                    ),
                ),
                (
                    "example_rfk",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_rfk_set",
                        to="example.examplerfk",
                    ),
                ),
                (
                    "example_rmtm",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_rfk_set",
                        to="example.examplermtm",
                    ),
                ),
                (
                    "example_roto",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_rfk_set",
                        to="example.exampleroto",
                    ),
                ),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="NestedExampleRMTM",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "example_ffk_set",
                    models.ManyToManyField(related_name="example_rmtm_set", to="example.exampleffk"),
                ),
                (
                    "example_fmtm_set",
                    models.ManyToManyField(related_name="example_rmtm_set", to="example.examplefmtm"),
                ),
                (
                    "example_foto_set",
                    models.ManyToManyField(related_name="example_rmtm_set", to="example.examplefoto"),
                ),
                (
                    "example_rfk_set",
                    models.ManyToManyField(related_name="example_rmtm_set", to="example.examplerfk"),
                ),
                (
                    "example_rmtm_set",
                    models.ManyToManyField(related_name="example_rmtm_set", to="example.examplermtm"),
                ),
                (
                    "example_roto_set",
                    models.ManyToManyField(related_name="example_rmtm_set", to="example.exampleroto"),
                ),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="NestedExampleROTO",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "example_ffk",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_roto",
                        to="example.exampleffk",
                    ),
                ),
                (
                    "example_fmtm",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_roto",
                        to="example.examplefmtm",
                    ),
                ),
                (
                    "example_foto",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_roto",
                        to="example.examplefoto",
                    ),
                ),
                (
                    "example_rfk",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_roto",
                        to="example.examplerfk",
                    ),
                ),
                (
                    "example_rmtm",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_roto",
                        to="example.examplermtm",
                    ),
                ),
                (
                    "example_roto",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="example_roto",
                        to="example.exampleroto",
                    ),
                ),
            ],
            options={
                "ordering": ["pk"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ExampleGeneric",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("object_id", models.PositiveIntegerField()),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["content_type", "object_id"],
                        name="example_exa_content_fc9d0f_idx",
                    )
                ],
            },
        ),
    ]
