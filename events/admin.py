from django.contrib import admin
from .models import Event, Category

class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'location')
    search_fields = ('name', 'description', 'location')
    list_filter = ('date', 'location')
    filter_horizontal = ('categories',)

admin.site.register(Event, EventAdmin)
admin.site.register(Category)
