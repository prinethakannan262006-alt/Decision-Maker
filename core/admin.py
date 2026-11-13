from django.contrib import admin
from .models import FAQ, ErrorCode, SupportTicket, Decision

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "category")
    list_filter = ("category",)
    search_fields = ("question", "answer")

@admin.register(ErrorCode)
class ErrorCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "title")
    search_fields = ("code", "title", "description")

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "email", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "user_message", "email")

@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "winner", "total_score", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "winner")
