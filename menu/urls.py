from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    path('', views.menu_view, name='menu'),
    path('transfer/', views.handle_transfer, name='handle_transfer'),
    path('recharge/', views.handle_recharge, name='handle_recharge'),
    path('verify/', views.verify_identity, name='verify_identity'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('verify_face_realtime/', views.verify_face_realtime, name='verify_face_realtime'),
    path('process_speech/', views.process_speech_command, name='process_speech'),
    path('verify_voice_realtime/', views.verify_voice_realtime, name='verify_voice_realtime'),


]
