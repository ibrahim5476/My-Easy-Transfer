from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser  # Assure-toi que ce modèle existe

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser  # Assurez-vous que ce modèle existe

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import CustomUser

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser

class CustomUserCreationForm(forms.ModelForm):
    """A form for creating new users that avoids MongoDB compatibility issues."""
    
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email']
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Simple direct equals check instead of iexact
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        validate_password(password2)
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user