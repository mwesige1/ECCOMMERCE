from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Profile
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/setup/', views.profile_setup, name='profile_setup'),
    path('profile/picture/upload/', views.upload_profile_picture, name='upload_profile_picture'),
    path('profile/picture/remove/', views.remove_profile_picture, name='remove_profile_picture'),

    # Password
    path('password/change/', views.change_password, name='change_password'),

    # Password Reset
    path('password-reset/',
         views.CustomPasswordResetView.as_view(),
         name='password_reset'),

    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset_done.html'
         ),
         name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html',
             success_url=reverse_lazy('users:password_reset_complete')
         ),
         name='password_reset_confirm'),

    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html'
         ),
         name='password_reset_complete'),

    # Addresses
    path('addresses/', views.address_list, name='address_list'),
    path('addresses/add/', views.address_add, name='address_add'),
    path('addresses/<int:pk>/edit/', views.address_edit, name='address_edit'),
    path('addresses/<int:pk>/delete/', views.address_delete, name='address_delete'),
    path('addresses/<int:pk>/set-default/', views.address_set_default, name='address_set_default'),

    # Account Settings
    path('settings/', views.account_settings, name='account_settings'),
    path('delete/', views.delete_account, name='delete_account'),

    # Legacy URLs
    path('update/', views.update_user, name='update_user'),
    path('update_password/', views.update_password, name='update_password'),
    path('user_info/', views.user_info, name='user_info'),
    path('profile/change-picture/', views.change_profile_picture, name='change_profile_picture'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)