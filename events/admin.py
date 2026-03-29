from django.contrib import admin

from .models import ParsedMessage, RoadEvent, EventVote, EventMedia

admin.site.register(ParsedMessage)
admin.site.register(RoadEvent)
admin.site.register(EventVote)
admin.site.register(EventMedia)

