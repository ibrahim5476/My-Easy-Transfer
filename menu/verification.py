import re
from paddleocr import PaddleOCR
import cv2
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import face_recognition
import os
import json

def information_verification(image_path, video):
    ocr = PaddleOCR(use_angle_cls=True, lang='en')

    passport_regex = re.compile(r'^[A-Z]\d{5,8}$')
    date_regex = re.compile(r"(\d{2}[\/\-]\d{2}[\/\-]\d{4})|(\d{4}[\/\-]\d{2}[\/\-]\d{2})")
    name_regex = re.compile(r'^[A-Z ]+$')
    cin_regex = re.compile(r'^\d{8}$')

    def extract_passport_number(lines):
        for line in lines:
            if passport_regex.search(line):
                return line
        return None

    def extract_name(lines):
        for line in lines:
            if name_regex.search(line) and len(line) >= 3:
                return line
        return None

    def extract_dates(lines):
        matches = [line for line in lines if date_regex.search(line)]
        if matches:
            dates = sorted(matches)
            return dates[:3] if len(dates) >= 3 else [None, None, None]
        return [None, None, None]

    def extract_cin(lines):
        for line in lines:
            if cin_regex.search(line):
                return line
        return None

    def verify_image(image_path, video):
        # Charger l'image et la convertir en RGB
        image1 = cv2.imread(image_path)
        if image1 is None:
            return False
        image1 = cv2.cvtColor(image1, cv2.COLOR_BGR2RGB)
        
        encodings_1 = face_recognition.face_encodings(image1)

        if len(encodings_1) == 0:
            return False

        cap = cv2.VideoCapture(video)
        if not cap.isOpened():
            return False

        frame_interval = int(cap.get(cv2.CAP_PROP_FPS) * 0.2)
        frame_count = 0
        match_found = False

        while not match_found:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % frame_interval == 0:
                # Convertir le frame en RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                encodings_2 = face_recognition.face_encodings(frame)

                if len(encodings_2) > 0:
                    match_found = face_recognition.compare_faces([encodings_1[0]], encodings_2[0])[0]
            frame_count += 1

        cap.release()
        return match_found

    def preprocess_image(image_path):
        img = Image.open(image_path).convert('L')
        img = ImageEnhance.Contrast(img).enhance(2)
        img = img.filter(ImageFilter.SHARPEN)
        img_array = np.array(img)
        _, binary_img = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
            img = Image.fromarray(img_array[y:y+h, x:x+w])
        return img

    ocr_result = ocr.ocr(np.array(preprocess_image(image_path)), cls=True)
    lines = [word_info[1][0] for line in ocr_result for word_info in line]

    data = {
        "NOM": extract_name(lines),
        "PRENOM": extract_name(lines),
        "NUM_PASSPORT": extract_passport_number(lines),
        "CIN": extract_cin(lines),
        "DATE_DE_NAISSANCE": extract_dates(lines)[0],
        "DATE_DE_DELIVRANCE": extract_dates(lines)[1],
        "DATE_D'EXPIRATION": extract_dates(lines)[2],
        "IMAGE_VERIFICATION": str(verify_image(image_path, video))
    }

    with open('data.json', 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    
    return data  # Ajouter cette ligne pour retourner le dictionnaire data
import librosa
import soundfile as sf
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from moviepy.editor import VideoFileClip
def extract_audio_from_video(video_path, output_audio_path):
    """Extrait l'audio d'une vidéo et le sauvegarde dans un fichier WAV"""
    try:
        import subprocess
        import os
        from django.conf import settings
        
        # Obtenir le chemin FFmpeg comme dans verify_voice_realtime
        ffmpeg_path = getattr(settings, 'FFMPEG_PATH', 'ffmpeg')
        
        # Essayer d'abord avec le chemin configuré ou la commande globale
        try:
            subprocess.run([
                ffmpeg_path, '-y', '-i', video_path,
                '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '1',
                output_audio_path
            ], check=True, capture_output=True)
        except FileNotFoundError:
            # Si ça échoue, essayer avec des chemins communs sur Windows
            potential_paths = [
                r'C:\\ffmpeg\\bin\\ffmpeg.exe',
                r'C:\ffmpeg\bin\ffmpeg.exe',
                r'C:\Users\%USERNAME%\AppData\Local\Programs\ffmpeg\bin\ffmpeg.exe'
            ]
            
            ffmpeg_found = False
            for path in potential_paths:
                expanded_path = os.path.expandvars(path)
                if os.path.exists(expanded_path):
                    subprocess.run([
                        expanded_path, '-y', '-i', video_path,
                        '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '1',
                        output_audio_path
                    ], check=True, capture_output=True)
                    ffmpeg_found = True
                    break
            
            if not ffmpeg_found:
                raise FileNotFoundError("FFmpeg n'a pas été trouvé sur le système")
                
        return True
    except Exception as e:
        print(f"Erreur lors de l'extraction audio: {e}")
        return False

def extract_voice_features(audio_path):
    """Extrait les caractéristiques MFCC de la voix"""
    try:
        # Vérifier que le fichier existe
        if not os.path.exists(audio_path):
            print(f"Le fichier audio n'existe pas: {audio_path}")
            return None
            
        print(f"Chargement du fichier audio: {audio_path}")
        # Charger l'audio et extraire les MFCCs
        y, sr = librosa.load(audio_path, sr=None)
        print(f"Audio chargé avec succès: {len(y)} échantillons, sr={sr}")
        
        # Supprimer les silences
        y_trimmed, _ = librosa.effects.trim(y, top_db=20)
        print(f"Audio traité après suppression des silences: {len(y_trimmed)} échantillons")
        
        # Extraire les MFCCs (caractéristiques vocales)
        mfccs = librosa.feature.mfcc(y=y_trimmed, sr=sr, n_mfcc=13)
        print(f"MFCCs extraits: forme {mfccs.shape}")
        
        # Calculer la moyenne des MFCCs sur l'axe du temps
        mfccs_mean = np.mean(mfccs, axis=1)
        print(f"Moyenne des MFCCs calculée: {mfccs_mean.shape}")
        
        return mfccs_mean
    except Exception as e:
        import traceback
        print(f"Erreur lors de l'extraction des caractéristiques vocales: {e}")
        print(traceback.format_exc())
        return None

def compare_voices(audio1_path, audio2_path):
    """
    Compare deux échantillons vocaux et retourne True s'ils sont identiques.
    Utilise une approche multi-caractéristiques avec des seuils de sécurité élevés.
    """
    try:
        import os
        import librosa
        import numpy as np
        from scipy.spatial.distance import cosine
        from scipy.stats import pearsonr
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"Comparaison vocale entre {audio1_path} et {audio2_path}")
        
        # 1. Vérification préliminaire des fichiers
        if not os.path.exists(audio1_path):
            logger.error(f"Fichier de référence introuvable: {audio1_path}")
            return False
            
        if not os.path.exists(audio2_path):
            logger.error(f"Fichier d'entrée introuvable: {audio2_path}")
            return False
            
        # 2. Vérification de la taille des fichiers
        min_file_size = 10000  # 10KB minimum
        if os.path.getsize(audio1_path) < min_file_size:
            logger.error(f"Fichier de référence trop petit: {os.path.getsize(audio1_path)} bytes")
            return False
            
        if os.path.getsize(audio2_path) < min_file_size:
            logger.error(f"Fichier d'entrée trop petit: {os.path.getsize(audio2_path)} bytes")
            return False
        
        # 3. Chargement des fichiers audio
        try:
            y1, sr1 = librosa.load(audio1_path, sr=None, res_type='kaiser_best')
            y2, sr2 = librosa.load(audio2_path, sr=None, res_type='kaiser_best')
        except Exception as e:
            logger.error(f"Erreur lors du chargement audio avec librosa: {e}")
            return False
        
        # 4. Vérification de la durée minimale
        min_duration = 1.5  # secondes
        if len(y1)/sr1 < min_duration or len(y2)/sr2 < min_duration:
            logger.error(f"Échantillons audio trop courts: {len(y1)/sr1}s et {len(y2)/sr2}s (min: {min_duration}s)")
            return False
        
        # 5. Normalisation des signaux
        y1 = librosa.util.normalize(y1)
        y2 = librosa.util.normalize(y2)
        
        # 6. Rééchantillonnage pour avoir la même fréquence
        if sr1 != sr2:
            logger.info(f"Rééchantillonnage de {sr2} Hz à {sr1} Hz")
            y2 = librosa.resample(y2, orig_sr=sr2, target_sr=sr1)
        
        # 7. Extraction de multiples caractéristiques
        # 7.1 MFCC (caractéristiques tonales)
        n_mfcc = 20
        mfcc1 = librosa.feature.mfcc(y=y1, sr=sr1, n_mfcc=n_mfcc)
        mfcc2 = librosa.feature.mfcc(y=y2, sr=sr1, n_mfcc=n_mfcc)
        
        # 7.2 Contraste spectral (timbre vocal)
        contrast1 = librosa.feature.spectral_contrast(y=y1, sr=sr1)
        contrast2 = librosa.feature.spectral_contrast(y=y2, sr=sr1)
        
        # 7.3 Chromagramme (contenu tonal)
        chroma1 = librosa.feature.chroma_stft(y=y1, sr=sr1)
        chroma2 = librosa.feature.chroma_stft(y=y2, sr=sr1)
        
        # 7.4 Fréquence fondamentale (hauteur de la voix)
        f0_1, voiced_flag1, _ = librosa.pyin(y1, fmin=librosa.note_to_hz('C2'), 
                                             fmax=librosa.note_to_hz('C7'), sr=sr1)
        f0_2, voiced_flag2, _ = librosa.pyin(y2, fmin=librosa.note_to_hz('C2'), 
                                             fmax=librosa.note_to_hz('C7'), sr=sr1)
        
        # Filtrer les valeurs non-nulles
        f0_1 = f0_1[~np.isnan(f0_1)]
        f0_2 = f0_2[~np.isnan(f0_2)]
        
        # 8. Calcul des similarités avec différentes métriques
        # 8.1 Similarité MFCC (cosinus)
        mfcc1_mean = np.mean(mfcc1, axis=1)
        mfcc2_mean = np.mean(mfcc2, axis=1)
        mfcc_similarity = max(0, 1 - cosine(mfcc1_mean, mfcc2_mean))
        
        # 8.2 Similarité de contraste spectral (cosinus)
        contrast1_mean = np.mean(contrast1, axis=1)
        contrast2_mean = np.mean(contrast2, axis=1)
        contrast_similarity = max(0, 1 - cosine(contrast1_mean, contrast2_mean))
        
        # 8.3 Similarité de chromagramme (corrélation)
        chroma1_mean = np.mean(chroma1, axis=1)
        chroma2_mean = np.mean(chroma2, axis=1)
        chroma_corr, _ = pearsonr(chroma1_mean, chroma2_mean)
        chroma_similarity = max(0, (chroma_corr + 1) / 2)  # Normalisation entre 0 et 1
        
        # 8.4 Similarité de fréquence fondamentale
        # (si les deux signaux ont des valeurs de pitch extraites)
        pitch_similarity = 0.0
        if len(f0_1) > 0 and len(f0_2) > 0:
            # Utiliser les histogrammes de fréquence fondamentale
            bins = np.linspace(50, 500, 50)  # Gamme typique de voix humaine
            hist1, _ = np.histogram(f0_1, bins=bins, density=True)
            hist2, _ = np.histogram(f0_2, bins=bins, density=True) 
            pitch_similarity = max(0, 1 - cosine(hist1, hist2))
        
        # 9. Combiner les scores avec des pondérations
        # Les poids sont attribués selon l'importance de chaque caractéristique
        weights = {
            'mfcc': 0.4,       # Très important pour l'identité vocale
            'contrast': 0.3,   # Important pour le timbre
            'chroma': 0.1,     # Moins important mais utile
            'pitch': 0.2       # Important pour distinguer les voix
        }
        
        # Calcul du score global
        final_similarity = (
            weights['mfcc'] * mfcc_similarity +
            weights['contrast'] * contrast_similarity +
            weights['chroma'] * chroma_similarity +
            weights['pitch'] * pitch_similarity
        )
        
        # 10. Logging des scores individuels pour le débogage
        logger.info(f"Scores de similarité:")
        logger.info(f"  - MFCC: {mfcc_similarity:.4f}")
        logger.info(f"  - Contraste: {contrast_similarity:.4f}")
        logger.info(f"  - Chroma: {chroma_similarity:.4f}")
        logger.info(f"  - Pitch: {pitch_similarity:.4f}")
        logger.info(f"  - Score final: {final_similarity:.4f}")
        
        # 11. Seuil de décision élevé pour la sécurité
        threshold = 0.80  # Seuil très strict
        result = final_similarity >= threshold
        
        logger.info(f"Résultat de la vérification vocale: {result} (score: {final_similarity:.4f}, seuil: {threshold})")
        return result
        
    except Exception as e:
        import traceback
        logger.error(f"Erreur critique dans compare_voices: {str(e)}")
        logger.error(traceback.format_exc())
        # En cas d'erreur, TOUJOURS refuser l'authentification
        return False

