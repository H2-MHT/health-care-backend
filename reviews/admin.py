from django.contrib import admin

# Register your models here.

from .models import Review, Reply

# class ReviewAdmin(admin.ModelAdmin):
#     list_display = ('id', 'patient')

class ReplyInline(admin.StackedInline):
    model = Reply
    extra = 1
    verbose_name = "Reply"
    verbose_name_plural = "Replies"

class ReviewAdmin(admin.ModelAdmin):
    inlines = [ReplyInline]

admin.site.register(Review, ReviewAdmin)