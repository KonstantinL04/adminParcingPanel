from django.contrib import admin

from .models import ParsedMessage, MessageLocation, MessageRouteMatch

admin.site.register(ParsedMessage)
admin.site.register(MessageLocation)
admin.site.register(MessageRouteMatch)

