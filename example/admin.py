from example.models import Client, Group
from pennyblack.models import NewsletterJobUnitAdmin

from django.contrib import admin

class ClientAdmin(admin.ModelAdmin):
    list_display = ('fullname', 'email')
    list_filter   = ('groups',)
    
admin.site.register(Client, ClientAdmin)
admin.site.register(Group, NewsletterJobUnitAdmin)
