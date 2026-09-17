from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('meetings', '0005_meeting_agenda_meeting_minutes'),
    ]

    operations = [
        # RenameModel (not Create+Delete) so the existing table and its
        # rows carry over intact - "meeting" becomes just one event_type
        # among several, not a whole new model replacing the old one.
        migrations.RenameModel(
            old_name='Meeting',
            new_name='Event',
        ),
        migrations.AddField(
            model_name='event',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('meeting', 'Meeting'),
                    ('flyout', 'Fly-Out'),
                    ('airshow', 'Airshow'),
                    ('social', 'Social'),
                    ('other', 'Other'),
                ],
                default='meeting',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='event',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='events',
                to='core.organization',
            ),
        ),
        migrations.AlterField(
            model_name='event',
            name='title',
            field=models.CharField(max_length=255),
        ),
    ]
