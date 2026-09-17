from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    # --- Zona pública (sin login) ---
    path("formularios/", views.lista_formularios, name="formularios"),
    path("formulario/", views.formulario_publico, name="formulario_general"),
    path("formulario/<str:codigo>/", views.formulario_publico, name="formulario_publico"),

    # --- Autenticación ---
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="panel/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # --- Zona privada (requiere login) ---
    path("", views.dashboard, name="dashboard"),
    path("indicador/<int:indicador_id>/", views.detalle_indicador, name="detalle_indicador"),
]
