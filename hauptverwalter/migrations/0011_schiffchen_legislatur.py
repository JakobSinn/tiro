from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("hauptverwalter", "0010_alter_antrag_wants_updates_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="schiffchen",
            name="legislatur",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="schiffchen",
                to="hauptverwalter.legislatur",
            ),
        ),
    ]
