"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views # Importa as views de autenticação
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from . import views

admin.site.site_header = 'Administrador Lana'
admin.site.site_title = 'Administrador Lana'
admin.site.index_title = 'Painel Administrativo Lana'


login_view = ensure_csrf_cookie(
    never_cache(
        auth_views.LoginView.as_view(
            template_name='registration/login.html',
            redirect_authenticated_user=True,
        )
    )
)

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    # Rotas de Autenticação
    path('login/', login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Seus outros apps
    path('chat/', include('chat.urls')),
    path('engine/', include('engine.urls')),
]
