from django.contrib import admin

# Register your models here.

from .models import Review, Reply

# class ReviewAdmin(admin.ModelAdmin):
#     list_display = ('id', 'patient')

admin.site.register(Review)
admin.site.register(Reply)