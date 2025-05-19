from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login
from django.shortcuts import render

from django.shortcuts import render, redirect

from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm
from .models import CustomUser
import os
import tempfile
from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import CustomUserCreationForm

from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import CustomUserCreationForm

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                return redirect('home')
            except Exception as e:
                # Log the error for debugging
                print(f"Error saving user: {e}")
                form.add_error(None, "An error occurred while creating your account.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'authentication/signup.html', {'form': form})

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm

from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import CustomUser

def home(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Authentifie l'utilisateur
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                # Redirige vers le menu après le login
                return redirect('menu:menu')
    else:
        form = AuthenticationForm()
    return render(request, 'authentication/home.html', {'form': form})
from django.contrib.auth.decorators import login_required
from .models import CustomUser

import os
import tempfile
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import CustomUser
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm

class CustomLoginView(LoginView):
    template_name = 'authentication/home.html'
    form_class = AuthenticationForm

    def get_success_url(self):
        return '/menu/'  # Redirige vers le menu après le login

home = CustomLoginView.as_view()
