from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adminparcing", "0005_route_chats"),
    ]

    operations = [
        migrations.AddField(
            model_name="alertcategory",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="category_icons/"),
        ),
    ]
