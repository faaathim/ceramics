from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('category_management', '0001_initial'),  
        ('product_management', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='category',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='products',
                to='category_management.category',
                null=True,  # temporarily allow null so it can migrate cleanly
            ),
        ),
    ]
