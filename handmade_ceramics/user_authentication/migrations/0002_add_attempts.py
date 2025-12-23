from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_authentication', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='otp',
            name='attempts',
            field=models.IntegerField(default=0),
        ),
    ]
