from django.urls import path
from . import views

urlpatterns = [
    # Pages
    path("", views.index, name="index"),
    path("decision-tool", views.decision_tool, name="decision_tool"),
    path("faqs", views.faqs, name="faqs"),
    path("error-codes", views.error_codes, name="error_codes"),
    path("support", views.support, name="support"),
    path("admin/tickets", views.admin_tickets, name="admin_tickets"),
    path("health", views.health_view, name="health"),
    path("trigger-error/<str:code_name>", views.trigger_error_view, name="trigger_error"),

    # REST APIs
    path("api/matrix/calculate", views.api_matrix_calculate, name="api_matrix_calculate"),
    path("api/matrix/save", views.api_matrix_save, name="api_matrix_save"),
    path("api/decisions", views.api_decisions, name="api_decisions"),
    path("api/chat", views.api_chat, name="api_chat"),
    path("api/feedback", views.api_feedback, name="api_feedback"),
    path("api/quick-picks/coin-flip", views.api_quick_picks_coin, name="api_quick_picks_coin"),
    path("api/quick-picks/dice-roll", views.api_quick_picks_dice, name="api_quick_picks_dice"),
    path("api/quick-picks/random-choice", views.api_quick_picks_random, name="api_quick_picks_random"),
    path("api/weather", views.api_weather, name="api_weather"),
    path("api/faqs", views.api_faqs, name="api_faqs"),
    path("api/error-codes", views.api_error_codes, name="api_error_codes"),
    path("api/support/tickets", views.api_tickets_list, name="api_tickets_list"),
    path("api/support/ticket", views.api_ticket_create, name="api_ticket_create"),
    path("api/support/ticket/<str:ticket_id>", views.api_ticket_detail, name="api_ticket_detail"),
    path("api/trigger-rate-limit", views.api_trigger_rate_limit, name="api_trigger_rate_limit"),
]
