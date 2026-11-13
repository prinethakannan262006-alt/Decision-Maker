from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("core.urls")),
]

# Custom Error Handlers
handler400 = "core.views.custom_bad_request_400"
handler403 = "core.views.custom_permission_denied_403"
handler404 = "core.views.custom_page_not_found_404"
handler500 = "core.views.custom_server_error_500"
