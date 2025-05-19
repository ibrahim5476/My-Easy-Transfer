from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import json
import shutil
import time
import re
from django.conf import settings
from django.http import HttpResponse, JsonResponse
import openai
from django.conf import settings
import requests

# Use your GROQ API key
GROQ_API_KEY = settings.GROQ_API_KEY  # add GROQ_API_KEY to your settings.py

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


# Importer la fonction de vérification
from .verification import information_verification

@login_required
def menu_view(request):
    # Réinitialiser les données de session lors de l'accès au menu principal
    if 'transfer_data' in request.session:
        del request.session['transfer_data']
    if 'transaction_type' in request.session:
        del request.session['transaction_type']
    
    return render(request, 'menu/menu.html')

@login_required
def handle_transfer(request):
    # Vérifier si l'utilisateur a déjà un profil enregistré
    client_dir_name = request.user.username
    client_dir = os.path.join(settings.MEDIA_ROOT, 'output', client_dir_name)
    json_path = os.path.join(client_dir, f"{request.user.username}.json")
    
    # Si le fichier JSON existe, rediriger directement vers le chatbot
    if os.path.exists(json_path):
        # Lire les données du fichier JSON pour les stocker en session
        with open(json_path, 'r', encoding='utf-8') as file:
            user_data = json.load(file)
            
        # Stocker des informations utiles dans la session pour le chatbot
        request.session['verified_user'] = {
            'name': user_data.get('NOM', '') + ' ' + user_data.get('PRENOM', ''),
            'cin': user_data.get('CIN', ''),
            'passport': user_data.get('NUM_PASSPORT', '')
        }
        request.session['transaction_type'] = 'transfer'
        return redirect('menu:chatbot')
    
    # Sinon, procéder à la vérification d'identité
    if request.method == 'POST':
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        
        if image and video:
            print(f"[handle_transfer] Image et vidéo reçus pour l'utilisateur {request.user.username}")
            # Sauvegarder temporairement les fichiers dans media/output/
            image_path = default_storage.save(os.path.join('output', f'temp_image_{request.user.username}.jpg'), ContentFile(image.read()))
            video_path = default_storage.save(os.path.join('output', f'temp_video_{request.user.username}.mp4'), ContentFile(video.read()))
            
            # Passer les chemins des fichiers à la session (chemin absolu)
            request.session['image_path'] = os.path.join(settings.MEDIA_ROOT, image_path)
            request.session['video_path'] = os.path.join(settings.MEDIA_ROOT, video_path)
            request.session['transaction_type'] = 'transfer'  # Stocker le type de transaction
            
            print(f"[handle_transfer] Chemins sauvegardés dans la session : image_path={request.session['image_path']}, video_path={request.session['video_path']}")
            
            # Rediriger vers la page de vérification
            return redirect('menu:verify_identity')
        else:
            print("[handle_transfer] Image ou vidéo manquante")
    return render(request, 'menu/transfer.html')

@login_required
def handle_recharge(request):
    # Vérifier si l'utilisateur a déjà un profil enregistré
    client_dir_name = request.user.username
    client_dir = os.path.join(settings.MEDIA_ROOT, 'output', client_dir_name)
    json_path = os.path.join(client_dir, f"{request.user.username}.json")
    
    # Si le fichier JSON existe, rediriger directement vers le chatbot
    if os.path.exists(json_path):
        # Lire les données du fichier JSON pour les stocker en session
        with open(json_path, 'r', encoding='utf-8') as file:
            user_data = json.load(file)
            
        # Stocker des informations utiles dans la session pour le chatbot
        request.session['verified_user'] = {
            'name': user_data.get('NOM', '') + ' ' + user_data.get('PRENOM', ''),
            'cin': user_data.get('CIN', ''),
            'passport': user_data.get('NUM_PASSPORT', '')
        }
        request.session['transaction_type'] = 'recharge'
        return redirect('menu:chatbot')
    
    # Sinon, procéder à la vérification d'identité
    if request.method == 'POST':
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        
        if image and video:
            print(f"[handle_recharge] Image et vidéo reçus pour l'utilisateur {request.user.username}")
            # Sauvegarder temporairement les fichiers dans media/output/
            image_path = default_storage.save(os.path.join('output', f'temp_image_{request.user.username}.jpg'), ContentFile(image.read()))
            video_path = default_storage.save(os.path.join('output', f'temp_video_{request.user.username}.mp4'), ContentFile(video.read()))
            
            # Passer les chemins des fichiers à la session (chemin absolu)
            request.session['image_path'] = os.path.join(settings.MEDIA_ROOT, image_path)
            request.session['video_path'] = os.path.join(settings.MEDIA_ROOT, video_path)
            request.session['transaction_type'] = 'recharge'  # Stocker le type de transaction
            
            print(f"[handle_recharge] Chemins sauvegardés dans la session : image_path={request.session['image_path']}, video_path={request.session['video_path']}")
            
            # Rediriger vers la page de vérification
            return redirect('menu:verify_identity')
        else:
            print("[handle_recharge] Image ou vidéo manquante")
    return render(request, 'menu/recharge.html')

@login_required
def verify_identity(request):
    # Code pour la vérification d'identité reste inchangé
    # ...
    
    # Chemin vers le dossier output dans MEDIA_ROOT
    output_dir = os.path.join(settings.MEDIA_ROOT, 'output')
    
    # Chemin vers le dossier racine du projet (pour vérifier data.json)
    project_root = settings.BASE_DIR
    
    # Assurez-vous que le dossier output existe
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Récupérer les chemins des fichiers de la session
    image_path = request.session.get('image_path')
    video_path = request.session.get('video_path')
    transaction_type = request.session.get('transaction_type', 'transfer')  # Par défaut 'transfer'
    
    print(f"[verify_identity] Chemins récupérés de la session : image_path={image_path}, video_path={video_path}, transaction_type={transaction_type}")
    
    if image_path and video_path:
        # Vérifier si les fichiers existent réellement
        if not os.path.exists(image_path) or not os.path.exists(video_path):
            print("[verify_identity] Un ou plusieurs fichiers temporaires n'existent pas")
            context = {
                'error': 'Les fichiers temporaires sont introuvables. Veuillez réessayer.'
            }
            return render(request, 'menu/verification.html', context)
        
        # Chemin du dossier spécifique pour cet utilisateur
        client_dir_name = request.user.username
        client_dir = os.path.join(output_dir, client_dir_name)
        
        # Chemin du fichier JSON dans le dossier spécifique
        json_path = os.path.join(client_dir, f"{request.user.username}.json")
        
        # Effectuer la vérification
        print(f"[verify_identity] Lancement de la vérification pour l'utilisateur {request.user.username}")
        new_data = information_verification(image_path, video_path)
        
        # Vérifier si new_data est None ou une structure invalide
        if new_data is None or not isinstance(new_data, dict):
            html_response = """
            <html>
                <body>
                    <h1>Échec de la Vérification d'Identité</h1>
                    <p>Une erreur est survenue lors de la vérification. Voulez-vous réessayer ?</p>
                    <script>
                        if (confirm("Une erreur est survenue. Voulez-vous réessayer ?")) {
                            window.location.href = "/menu/transfer/";
                        } else {
                            window.location.href = "/menu/";
                        }
                    </script>
                </body>
            </html>
            """
            # Nettoyer les fichiers temporaires avant de retourner
            if os.path.exists(image_path):
                os.remove(image_path)
            if os.path.exists(video_path):
                os.remove(video_path)
            
            # Supprimer les données de la session
            if 'image_path' in request.session:
                del request.session['image_path']
            if 'video_path' in request.session:
                del request.session['video_path']
            if 'transaction_type' in request.session:
                del request.session['transaction_type']
            
            # Supprimer data.json s'il existe dans le dossier racine
            data_json_path = os.path.join(project_root, 'data.json')
            if os.path.exists(data_json_path):
                os.remove(data_json_path)
            
            return HttpResponse(html_response)
        
        # Vérifier si l'image verification est "False"
        if isinstance(new_data, dict) and new_data.get('IMAGE_VERIFICATION') == "False":
            print("[verify_identity] Échec de la vérification d'image (IMAGE_VERIFICATION=False)")
            redirect_url = "/menu/recharge/" if transaction_type == "recharge" else "/menu/transfer/"
            html_response = f"""
            <html>
                <body>
                    <h1>Échec de la Vérification d'Identité</h1>
                    <p>L'image de vérification a échoué. Voulez-vous réessayer ?</p>
                    <script>
                        if (confirm("L'image de vérification a échoué. Voulez-vous réessayer ?")) {{
                            window.location.href = "{redirect_url}";
                        }} else {{
                            window.location.href = "/menu/";
                        }}
                    </script>
                </body>
            </html>
            """
            # Ne pas nettoyer les fichiers temporaires ici, car l'utilisateur peut réessayer
            # Supprimer data.json s'il existe dans le dossier racine
            data_json_path = os.path.join(project_root, 'data.json')
            if os.path.exists(data_json_path):
                os.remove(data_json_path)
            
            return HttpResponse(html_response)
        
        # Vérifier si un fichier JSON existe déjà pour cet utilisateur
        if os.path.exists(json_path):
            print(f"[verify_identity] Fichier JSON existant trouvé : {json_path}")
            # Charger les données existantes
            with open(json_path, 'r', encoding='utf-8') as existing_file:
                existing_data = json.load(existing_file)
            
            # Comparer les clés importantes entre les deux ensembles de données
            keys_to_compare = ["NOM", "PRENOM", "NUM_PASSPORT", "CIN", "DATE_DE_NAISSANCE", "DATE_DE_DELIVRANCE", "DATE_D'EXPIRATION"]
            
            is_conform = True
            for key in keys_to_compare:
                if existing_data.get(key) != new_data.get(key):
                    is_conform = False
                    break
            
            if is_conform:
                # Si conforme, utiliser les données existantes pour la sauvegarde
                print("[verify_identity] Les données sont conformes avec l'enregistrement existant")
                
                # Nettoyer les fichiers temporaires
                if os.path.exists(image_path):
                    os.remove(image_path)
                if os.path.exists(video_path):
                    os.remove(video_path)
                
                # Supprimer data.json s'il existe dans le dossier racine
                data_json_path = os.path.join(project_root, 'data.json')
                if os.path.exists(data_json_path):
                    os.remove(data_json_path)
                
                # Stocker des informations utiles dans la session pour le chatbot
                request.session['verified_user'] = {
                    'name': existing_data.get('NOM', '') + ' ' + existing_data.get('PRENOM', ''),
                    'cin': existing_data.get('CIN', ''),
                    'passport': existing_data.get('NUM_PASSPORT', '')
                }
                
                # Supprimer les chemins des fichiers temporaires de la session
                if 'image_path' in request.session:
                    del request.session['image_path']
                if 'video_path' in request.session:
                    del request.session['video_path']
                
                # Rediriger vers l'interface chatbot
                return redirect('menu:chatbot')
            else:
                # Si non conforme, afficher un message et permettre de réessayer
                print("[verify_identity] Les données ne sont pas conformes avec l'enregistrement existant")
                redirect_url = "/menu/recharge/" if transaction_type == "recharge" else "/menu/transfer/"
                html_response = f"""
                <html>
                    <body>
                        <h1>Échec de la Vérification d'Identité</h1>
                        <p>Les données ne sont pas conformes avec l'enregistrement existant. Voulez-vous réessayer ?</p>
                        <script>
                            if (confirm("Les données ne sont pas conformes. Voulez-vous réessayer ?")) {{
                                window.location.href = "{redirect_url}";
                            }} else {{
                                window.location.href = "/menu/";
                            }}
                        </script>
                    </body>
                </html>
                """
                # Nettoyer les fichiers temporaires avant de retourner
                if os.path.exists(image_path):
                    os.remove(image_path)
                if os.path.exists(video_path):
                    os.remove(video_path)
                
                # Supprimer les données de la session
                if 'image_path' in request.session:
                    del request.session['image_path']
                if 'video_path' in request.session:
                    del request.session['video_path']
                if 'transaction_type' in request.session:
                    del request.session['transaction_type']
                
                # Supprimer data.json s'il existe dans le dossier racine
                data_json_path = os.path.join(project_root, 'data.json')
                if os.path.exists(data_json_path):
                    os.remove(data_json_path)
                
                return HttpResponse(html_response)
        else:
            # Si aucun fichier JSON existant, sauvegarder les nouvelles données
            print("[verify_identity] Aucun fichier JSON existant, sauvegarde des nouvelles données")
            
            # Créer le dossier spécifique pour cet utilisateur
            if not os.path.exists(client_dir):
                os.makedirs(client_dir)
            
            # Sauvegarder le fichier JSON dans le dossier spécifique
            with open(json_path, 'w', encoding='utf-8') as file:
                json.dump(new_data, file, ensure_ascii=False, indent=4)
            
            # Déplacer l'image et la vidéo dans le dossier spécifique
            final_image_path = os.path.join(client_dir, 'image.jpg')
            final_video_path = os.path.join(client_dir, 'video.mp4')
            
            if os.path.exists(image_path):
                shutil.move(image_path, final_image_path)
            if os.path.exists(video_path):
                shutil.move(video_path, final_video_path)
            
            # Stocker des informations utiles dans la session pour le chatbot
            request.session['verified_user'] = {
                'name': new_data.get('NOM', '') + ' ' + new_data.get('PRENOM', ''),
                'cin': new_data.get('CIN', ''),
                'passport': new_data.get('NUM_PASSPORT', '')
            }
            
            # Supprimer les chemins des fichiers temporaires de la session
            if 'image_path' in request.session:
                del request.session['image_path']
            if 'video_path' in request.session:
                del request.session['video_path']
            
            # Supprimer data.json s'il existe dans le dossier racine
            data_json_path = os.path.join(project_root, 'data.json')
            if os.path.exists(data_json_path):
                os.remove(data_json_path)
            
            # Rediriger vers l'interface chatbot
            return redirect('menu:chatbot')
    else:
        print("[verify_identity] Aucun fichier à vérifier dans la session")
        context = {
            'error': 'Aucun fichier à vérifier'
        }
        
        # Supprimer data.json s'il existe dans le dossier racine
        data_json_path = os.path.join(project_root, 'data.json')
        if os.path.exists(data_json_path):
            os.remove(data_json_path)
        
        return render(request, 'menu/verification.html', context)

# Vues pour le chatbot
@login_required
def chatbot_view(request):
    # Récupérer le type de transaction de la session
    transaction_type = request.session.get('transaction_type', 'transfer')
    
    # Récupérer les informations de l'utilisateur vérifié
    verified_user = request.session.get('verified_user', {})
    
    # Initialiser les variables pour la caméra et le micro
    context = {
        'transaction_type': transaction_type,
        'verified_user': verified_user,
        'show_camera': True,  # Activer la caméra par défaut
        'show_microphone': True,  # Activer le micro par défaut
        'initial_message': f"Bonjour {verified_user.get('name', '')}, je suis votre assistant virtuel. Comment puis-je vous aider avec votre {transaction_type_text(transaction_type)} ?"
    }
    
    return render(request, 'menu/chatbot.html', context)

@login_required
def verify_face_realtime(request):
    """Point d'entrée API pour vérifier le visage en temps réel avec la webcam"""
    if request.method == 'POST':
        try:
            # Récupérer l'image de la webcam envoyée par le frontend
            if 'image' not in request.FILES:
                return JsonResponse({'success': False, 'message': 'Aucune image reçue'})
            
            webcam_image = request.FILES['image']
            
            # Sauvegarder temporairement l'image
            temp_image_path = default_storage.save(os.path.join('output', f'temp_webcam_{request.user.username}.jpg'), ContentFile(webcam_image.read()))
            temp_image_full_path = os.path.join(settings.MEDIA_ROOT, temp_image_path)
            
            # Récupérer le chemin de l'image de référence
            reference_image_path = os.path.join(settings.MEDIA_ROOT, 'output', request.user.username, 'image.jpg')
            
            if not os.path.exists(reference_image_path):
                # Nettoyer le fichier temporaire
                if os.path.exists(temp_image_full_path):
                    os.remove(temp_image_full_path)
                return JsonResponse({'success': False, 'message': 'Image de référence introuvable'})
            
            # Importer la fonction de vérification ici pour éviter les problèmes de dépendances circulaires
            from .verification import information_verification
            import face_recognition
            
            # Fonction simplifiée pour comparer deux images
            def compare_faces(image1_path, image2_path):
                try:
                    image1 = face_recognition.load_image_file(image1_path)
                    encodings_1 = face_recognition.face_encodings(image1)
                    
                    if len(encodings_1) == 0:
                        return False
                    
                    image2 = face_recognition.load_image_file(image2_path)
                    encodings_2 = face_recognition.face_encodings(image2)
                    
                    if len(encodings_2) == 0:
                        return False
                    
                    return face_recognition.compare_faces([encodings_1[0]], encodings_2[0])[0]
                except Exception as e:
                    print(f"Erreur lors de la comparaison des visages: {e}")
                    return False
            
            # Vérifier la correspondance des visages
            is_match = compare_faces(reference_image_path, temp_image_full_path)
            
            # Nettoyer le fichier temporaire
            if os.path.exists(temp_image_full_path):
                os.remove(temp_image_full_path)
            
            if is_match:
                # Si la vérification réussit, marquer la session comme vérifiée en temps réel
                request.session['realtime_verified'] = True
                request.session.modified = True
                return JsonResponse({'success': True, 'message': 'Vérification faciale réussie'})
            else:
                return JsonResponse({'success': False, 'message': 'Vérification faciale échouée'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Erreur lors de la vérification: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)



def process_speech_command(request):
    """Point d'entrée API pour traiter les commandes vocales de l'utilisateur"""
    if request.method == 'POST':
        try:
            # Vérifier si l'utilisateur a passé la vérification faciale ET vocale
            if not request.session.get('realtime_verified', False):
                return JsonResponse({'error': 'Veuillez d\'abord effectuer la vérification faciale en temps réel'}, status=403)
            
            if not request.session.get('voice_verified', False):
                return JsonResponse({'error': 'Veuillez d\'abord effectuer la vérification vocale'}, status=403)
            
            data = json.loads(request.body)
            speech_text = data.get('speech_text', '')
            
            # Récupérer le type de transaction initial de la session
            transaction_type = request.session.get('transaction_type', 'transfer')
            
            # Traiter la commande utilisateur avec le nouveau système OpenAI
            response_data = process_user_command(speech_text, request, transaction_type)
            
            return JsonResponse(response_data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Format JSON invalide'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
import logging
logger = logging.getLogger(__name__)
def verify_voice_realtime(request):
    """Point d'entrée API pour vérifier la voix en temps réel avec le microphone"""
    if request.method == 'POST':
        try:
            logger.debug("Début de la vérification vocale en temps réel")
            
            # Vérifier la vérification faciale
            if not request.session.get('realtime_verified', False):
                logger.warning("Vérification faciale non effectuée")
                return JsonResponse({'success': False, 'message': 'Veuillez d\'abord effectuer la vérification faciale'})
            
            # Récupérer l'audio
            if 'audio' not in request.FILES:
                logger.error("Aucun fichier audio reçu dans la requête")
                return JsonResponse({'success': False, 'message': 'Aucun audio reçu'})
            
            audio_blob = request.FILES['audio']
            logger.debug(f"Taille du fichier audio reçu: {audio_blob.size} octets")
            
            # Créer les répertoires nécessaires
            user_dir = os.path.join(settings.MEDIA_ROOT, 'output', request.user.username)
            os.makedirs(user_dir, exist_ok=True)
            
            # CORRECTION: Vérifier le format et convertir si nécessaire
            # Utiliser un format audio WAV standard
            temp_filename = f'temp_audio_{request.user.username}_{int(time.time())}.wav'
            temp_dir = os.path.join('output', request.user.username)
            temp_audio_path = os.path.join(temp_dir, temp_filename)
            temp_audio_full_path = os.path.join(settings.MEDIA_ROOT, temp_audio_path)
            
            # Sauvegarder le blob audio brut temporairement
            raw_audio_path = os.path.join(settings.MEDIA_ROOT, temp_dir, f"raw_{temp_filename}")
            with open(raw_audio_path, 'wb') as f:
                audio_blob.seek(0)
                f.write(audio_blob.read())
            
            # Définir le chemin FFmpeg - d'abord essayer la configuration, puis des chemins courants
            ffmpeg_path = getattr(settings, 'FFMPEG_PATH', 'ffmpeg')
            
            # Convertir en WAV avec FFmpeg (format reconnu par librosa)
            import subprocess
            try:
                # Essayer d'abord avec le chemin configuré ou la commande globale
                try:
                    subprocess.run([
                        ffmpeg_path, '-y', '-i', raw_audio_path, 
                        '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '1',
                        temp_audio_full_path
                    ], check=True, capture_output=True)
                    logger.debug(f"Audio converti et sauvegardé à: {temp_audio_full_path}")
                except FileNotFoundError:
                    # Si ça échoue, essayer avec des chemins communs sur Windows
                    logger.warning("FFmpeg non trouvé dans le PATH, essai avec les chemins courants")
                    potential_paths = [
                        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
                        r'C:\ffmpeg\bin\ffmpeg.exe',
                        r'C:\Users\%USERNAME%\AppData\Local\Programs\ffmpeg\bin\ffmpeg.exe'
                    ]
                    
                    ffmpeg_found = False
                    for path in potential_paths:
                        expanded_path = os.path.expandvars(path)  # Remplacer %USERNAME% par la variable d'environnement
                        if os.path.exists(expanded_path):
                            logger.debug(f"FFmpeg trouvé à: {expanded_path}")
                            subprocess.run([
                                expanded_path, '-y', '-i', raw_audio_path, 
                                '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '1',
                                temp_audio_full_path
                            ], check=True, capture_output=True)
                            ffmpeg_found = True
                            break
                    
                    if not ffmpeg_found:
                        raise FileNotFoundError("FFmpeg n'a pas été trouvé sur le système")
                
                # Supprimer le fichier temporaire brut
                os.remove(raw_audio_path)
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Erreur lors de la conversion audio: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}")
                
                # SOLUTION ALTERNATIVE: En mode développement/test
                if settings.DEBUG:
                    request.session['voice_verified'] = True
                    request.session.modified = True
                    logger.warning("Mode test activé - vérification vocale simulée comme réussie")
                    return JsonResponse({'success': True, 'message': 'Vérification vocale réussie (MODE TEST)'})
                else:
                    return JsonResponse({'success': False, 'message': 'Erreur lors de la conversion audio'})
            
            except FileNotFoundError as e:
                logger.error(f"FFmpeg non trouvé: {str(e)}")
                
                # En mode développement, continuer avec la simulation
                if settings.DEBUG:
                    request.session['voice_verified'] = True
                    request.session.modified = True
                    logger.warning("Mode test activé - vérification vocale simulée comme réussie")
                    return JsonResponse({'success': True, 'message': 'Vérification vocale réussie (MODE TEST)'})
                else:
                    return JsonResponse({'success': False, 'message': 'FFmpeg non trouvé sur le système'})
            
            # Vidéo de référence
            reference_video_path = os.path.join(settings.MEDIA_ROOT, 'output', request.user.username, 'video.mp4')
            logger.debug(f"Chemin vidéo de référence: {reference_video_path}")
            
            # Vérifier si la vidéo existe
            if not os.path.exists(reference_video_path):
                logger.error(f"Vidéo de référence introuvable à {reference_video_path}")
                
                # Pour des tests rapides en mode développement
                if settings.DEBUG:
                    request.session['voice_verified'] = True
                    request.session.modified = True
                    logger.warning("Mode test activé - vérification vocale simulée comme réussie")
                    return JsonResponse({'success': True, 'message': 'Vérification vocale réussie (MODE TEST)'})
                else:
                    return JsonResponse({'success': False, 'message': 'Vidéo de référence introuvable'})
            
            # Extraire audio de référence
            reference_audio_path = os.path.join(settings.MEDIA_ROOT, 'output', request.user.username, 'reference_audio.wav')
            logger.debug(f"Chemin audio de référence: {reference_audio_path}")
            
            # Vérifier si l'audio de référence existe déjà
            if not os.path.exists(reference_audio_path):
                logger.debug("Extraction de l'audio depuis la vidéo de référence")
                from .verification import extract_audio_from_video
                extraction_success = extract_audio_from_video(reference_video_path, reference_audio_path)
                
                if not extraction_success:
                    logger.error("Échec de l'extraction audio depuis la vidéo")
                    if os.path.exists(temp_audio_full_path):
                        os.remove(temp_audio_full_path)
                    return JsonResponse({'success': False, 'message': "Impossible d'extraire l'audio de référence"})
            
            # Comparer les échantillons vocaux
            logger.debug("Comparaison des échantillons vocaux")
            from .verification import compare_voices
            is_match = compare_voices(reference_audio_path, temp_audio_full_path)
            logger.debug(f"Résultat de la comparaison vocale: {is_match}")
            
            # Nettoyer le fichier temporaire
            if os.path.exists(temp_audio_full_path):
                os.remove(temp_audio_full_path)
                logger.debug("Fichier audio temporaire supprimé")
            
            if is_match:
                request.session['voice_verified'] = True
                request.session.modified = True
                logger.info("Vérification vocale réussie pour l'utilisateur")
                return JsonResponse({'success': True, 'message': 'Vérification vocale réussie'})
            else:
                logger.warning("Échec de la vérification vocale")
                return JsonResponse({'success': False, 'message': 'Vérification vocale échouée'})
            
        except Exception as e:
            logger.exception(f"Exception lors de la vérification vocale: {str(e)}")
            
            # En développement, renvoyer les détails de l'erreur
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Détails de l'erreur: {error_details}")
            
            return JsonResponse({
                'success': False, 
                'message': f'Erreur lors de la vérification vocale: {str(e)}',
                'details': error_details if settings.DEBUG else None
            })
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

# Ajoutez ces imports au début du fichier views.py
from .transaction_processor import process_conversation, save_transaction, extract_transaction_data, update_transfer_data

# Remplacer la fonction process_user_command existante par celle-ci
def process_user_command(speech_text, request, transaction_type='transfer'):
    """Process user's speech command using GROQ API."""
    if 'chat_history' not in request.session:
        request.session['chat_history'] = []

    if 'transfer_data' not in request.session:
        request.session['transfer_data'] = {
            'step': 'initial',
            'recipient_name': None,
            'address': None,
            'phone_number': None,
            'amount': None,
            'confirmed': False,
            'completed': False
        }

    transfer_data = request.session['transfer_data']
    chat_history = request.session['chat_history']

    # Initialiser l'historique si vide
    if not chat_history:
        system_message = {"role": "system", "content": f"""Vous êtes un assistant virtuel professionnel pour My Easy Transfer, spécialisé dans les transferts d'argent et recharges mobiles.

PAYS DE DESTINATION :
- Uniquement la Tunisie et le Maroc
- Refuser toute demande vers d'autres pays

PROCESSUS DE TRANSACTION :
Transfert d'argent :
1. Nom du bénéficiaire
2. Adresse (uniquement en Tunisie ou au Maroc)
3. Numéro de téléphone
4. Montant

Recharge mobile :
1. Numéro de téléphone (Tunisie ou Maroc)
2. Opérateur
3. Montant

CONFIRMATION OBLIGATOIRE :
À la fin de chaque transaction, vous devez TOUJOURS répéter toutes les informations dans cet ordre exact :
"Veuillez confirmer ces informations :
- Nom du bénéficiaire : [nom]
- Adresse : [adresse]
- Numéro de téléphone : [téléphone]
- Montant : [montant]
Est-ce correct ?"

RÈGLES IMPORTANTES :
1. Vérifier que l'adresse est bien en Tunisie ou au Maroc
2. Attendre la confirmation de l'utilisateur avant de finaliser
3. En cas d'erreur dans les informations, permettre la correction
4. Ne jamais procéder sans avoir répété et confirmé toutes les informations

Vous gérez actuellement : {transaction_type_text(transaction_type)}"""}
        chat_history.append(system_message)

    # Ajouter le message utilisateur
    chat_history.append({"role": "user", "content": speech_text})
    
    try:
        # Mode secours si DEBUG est activé
        if settings.DEBUG and 'GROQ_FALLBACK' in os.environ:
            print("Mode secours activé - simulation de réponse API")
            # Simuler une réponse API basique
            ai_response = f"J'ai bien reçu votre demande concernant {speech_text}"
            
            # Traiter la demande manuellement
            if 'transfer' in speech_text.lower() and 'dinar' in speech_text.lower():
                # Extraire les données directement avec notre nouveau système
                extracted_data = extract_transaction_data(speech_text, transaction_type)
                transfer_data = update_transfer_data(transfer_data, extracted_data)
                
                if transfer_data['step'] == 'confirmation':
                    ai_response = f"Pour confirmer, je vais transférer {transfer_data.get('amount')} dinars à {transfer_data.get('recipient_name')} à {transfer_data.get('address')} au numéro {transfer_data.get('phone_number')}. Est-ce correct?"
            
            # Utiliser notre nouveau système de détection de confirmation
            transaction_id, transfer_data = process_conversation(request, chat_history, transfer_data, transaction_type)
            if transaction_id:
                ai_response = f"Transaction confirmée ! ID: {transaction_id}"
        else:
            # Code normal avec GROQ API
            payload = {
                "model": "llama3-70b-8192",
                "messages": chat_history,
                "max_tokens": 150,
                "temperature": 0.5,
            }
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            }

            # Log de débogage
            print(f"Sending request to GROQ with payload: {json.dumps(payload, default=str)}")
            
            response = requests.post(GROQ_ENDPOINT, json=payload, headers=headers)
            
            # Log détaillé de la réponse en cas d'erreur
            if response.status_code != 200:
                print(f"GROQ API error: Status {response.status_code}, Response: {response.text}")
                raise Exception(f"GROQ API returned status {response.status_code}: {response.text}")
                
            response.raise_for_status()
            result = response.json()

            ai_response = result['choices'][0]['message']['content']

        # Sauvegarder la réponse dans l'historique
        chat_history.append({"role": "assistant", "content": ai_response})
        request.session['chat_history'] = chat_history

        # NOUVEAU: Utiliser notre système d'extraction avancé pour mettre à jour les données
        # Extraire des données du message utilisateur
        extracted_data = extract_transaction_data(speech_text, transaction_type)
        transfer_data = update_transfer_data(transfer_data, extracted_data)
        
        # Vérifier si c'est une confirmation et traiter la transaction
        transaction_id, updated_transfer_data = process_conversation(request, chat_history, transfer_data, transaction_type)
        request.session['transfer_data'] = updated_transfer_data
        
        # Si une transaction a été confirmée et enregistrée
        if transaction_id:
            return {
                'type': 'transaction_confirmed',
                'message': ai_response + f"\n\nTransaction confirmée ! ID: {transaction_id}",
                'transaction_id': transaction_id
            }

        return {
            'type': updated_transfer_data['step'],
            'message': ai_response,
            'transfer_data': updated_transfer_data
        }

    except Exception as e:
        print(f"Error using GROQ: {str(e)}")
        # Mode secours en cas d'erreur
        if settings.DEBUG:
            # En développement, simuler une réponse simple
            ai_response = "J'ai bien compris votre demande. En mode secours suite à une erreur API."
            
            # Utiliser notre nouveau système d'extraction même en cas d'erreur
            extracted_data = extract_transaction_data(speech_text, transaction_type)
            transfer_data = update_transfer_data(transfer_data, extracted_data)
            request.session['transfer_data'] = transfer_data
            
            return {
                'type': transfer_data['step'],
                'message': ai_response + " (Mode secours activé)",
                'transfer_data': transfer_data
            }
        return {
            'type': 'error',
            'message': f"Désolé, une erreur est survenue: {str(e)}"
        }

# Ajoutez cette fonction pour compléter le code (elle est référencée mais non définie dans l'extrait original)
def transaction_type_text(transaction_type):
    """Retourne un texte descriptif pour le type de transaction."""
    if transaction_type == 'transfer':
        return "le transfert d'argent"
    elif transaction_type == 'recharge':
        return "la recharge mobile"
    else:
        return "la transaction"

# Ajoutez cette fonction pour vérifier si tous les champs requis sont présents
def all_required_fields_present(data, transaction_type):
    """Vérifie si tous les champs requis pour une transaction sont présents."""
    if transaction_type == 'transfer':
        return all(data.get(field) for field in ['recipient_name', 'address', 'phone_number', 'amount'])
    else:  # recharge
        return all(data.get(field) for field in ['phone_number', 'amount'])

# Fonction pour enregistrer la transaction dans la base de données (si besoin)
def register_transaction(request, transfer_data, transaction_type):
    """Enregistre la transaction et retourne son ID."""
    from .transaction_processor import save_transaction
    
    # Générer et retourner un ID de transaction
    transaction_id = save_transaction(request.user.username, transfer_data, transaction_type)
    return transaction_id 