from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect
from django import forms


class CustomAuthForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Password',
        })
    )

    error_messages = {
        'invalid_login': 'Invalid username or password. Please try again.',
        'inactive': 'This account has been disabled.',
    }


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomAuthForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return '/dashboard/'


class CustomLogoutView(LogoutView):
    next_page = '/accounts/login/'
