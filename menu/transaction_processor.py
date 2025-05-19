import os
import json
import re
import uuid
from datetime import datetime
from django.conf import settings

def detect_confirmation(message):
    """
    Détecte si le message contient une confirmation.
    
    Args:
        message (str): Le message de l'utilisateur
    
    Returns:
        bool: True si une confirmation est détectée, False sinon
    """
    confirmation_keywords = [
        "confirme",  "je confirme", "c'est correct",
        "valider", "accepte", "approuve", "exact", "tout à fait",
        "validé", "correct", "c'est bon", "parfait", "procéder", "ça me va", "go",
        "allez-y", "vas-y", "confirmons", "bien sûr", "certainement", "absolutely", "yes"
    ]
    
    # Traiter le message: convertir en minuscules et supprimer la ponctuation
    message_lower = message.lower()
    message_clean = re.sub(r'[^\w\s]', '', message_lower)
    
    # Vérifier si le message contient un mot de confirmation isolé
    words = message_clean.split()
    for word in words:
        if word in confirmation_keywords:
            return True
    
    # Vérifier si le message contient une expression de confirmation
    for keyword in confirmation_keywords:
        if keyword in message_lower:
            # Eviter les faux positifs
            negation_patterns = [
                r"ne\s+\w+\s+pas\s+" + keyword,
                r"pas\s+" + keyword,
                r"non\s+\w*\s*" + keyword
            ]
            
            if any(re.search(pattern, message_lower) for pattern in negation_patterns):
                continue
                
            return True
    
    # Vérifier les phrases d'affirmation courtes
    affirmative_phrases = [
        r"^oui\.?$", 
        r"^ok\.?$", 
        r"^d'accord\.?$",
        r"^je\s+confirme\.?$",
        r"^c'est\s+correct\.?$",
        r"^c'est\s+bon\.?$",
        r"^parfait\.?$"
    ]
    
    for pattern in affirmative_phrases:
        if re.search(pattern, message_lower):
            return True
    
    return False

def extract_transaction_data(message, transaction_type='transfer'):
    """
    Extrait les informations de transaction du message de l'utilisateur.
    
    Args:
        message (str): Le message de l'utilisateur
        transaction_type (str): Le type de transaction ('transfer' ou 'recharge')
    
    Returns:
        dict: Les informations extraites
    """
    data = {}
    
    if transaction_type == 'transfer':
        # Extraction du nom du bénéficiaire - patrons élargis
        name_patterns = [
            r"à\s+([A-Za-zÀ-ÿ\s]+?)\s+(?:situé|qui|au|en|dont|avec|sur)",
            r"pour\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+(?:situé|qui|au|en|dont|avec|sur)|\s+\d)",
            r"envoyer\s+\w+\s+à\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+(?:situé|qui|au|en|dont|avec|sur)|\s+\d)",
            r"(?:envoi|transférer|virement)\s+(?:à|pour)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+|$)",
            r"(?:nom|bénéficiaire)\s+(?:est|:|s'appelle)?\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+|$)"
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, message, re.IGNORECASE)
            if name_match:
                potential_name = name_match.group(1).strip()
                # Vérifier que le nom n'est pas trop long (pour éviter de capturer des phrases)
                if len(potential_name.split()) <= 5:
                    data['recipient_name'] = potential_name
                    break
        
        # Extraction directe du nom si c'est uniquement un nom (comme un message isolé)
        # Ceci résout le problème d'extraction quand le message contient uniquement "Aymen Ben Halima"
        if not data.get('recipient_name') and len(message.strip().split()) <= 5:
            name_only_pattern = r"^([A-Za-zÀ-ÿ\s]+)$"
            name_only_match = re.search(name_only_pattern, message.strip())
            if name_only_match:
                data['recipient_name'] = name_only_match.group(1).strip()
        
        # Extraction de l'adresse - patrons élargis
        address_patterns = [
            r"(?:situé|habite|habite à|demeure|vit)(?:\s+(?:à|en|au))?\s+([A-Za-zÀ-ÿ\s,0-9]+?)(?:\s+(?:et|dont|avec|au numéro|ayant|qui a)|\.|$)",
            r"adresse\s+(?:est|:)?\s+([A-Za-zÀ-ÿ\s,0-9]+?)(?:\s+(?:et|dont|avec|au numéro|ayant|qui a)|\.|$)",
            r"(?:à|en|au)\s+([A-Za-zÀ-ÿ\s,0-9]+?)(?:\s+(?:qui|dont|avec|au numéro)|\.|$)",
            r"destination\s+(?:est|:)?\s+([A-Za-zÀ-ÿ\s,0-9]+?)(?:\s+|\.|\,|$)"
        ]
        
        for pattern in address_patterns:
            address_match = re.search(pattern, message, re.IGNORECASE)
            if address_match:
                data['address'] = address_match.group(1).strip()
                break
                
        # Extraction directe de l'adresse s'il s'agit d'un message contenant uniquement une adresse
        # Ceci résout le problème d'extraction quand le message contient uniquement "adresse Tunis Hammamet"
        if not data.get('address'):
            address_only_pattern = r"^(?:adresse\s+)?([A-Za-zÀ-ÿ\s,0-9]+)$"
            address_only_match = re.search(address_only_pattern, message.strip())
            if address_only_match and "adresse" in message.lower():
                data['address'] = address_only_match.group(1).strip()
    
    # Extraction du numéro de téléphone (commun aux deux types)
    phone_patterns = [
        r"(?:téléphone|portable|numéro|contact|joignable)(?:\s+(?:est|au|:))?\s+(\+?[0-9]{1,4}[\s\-\.]?[0-9]{2,}[\s\-\.]?[0-9]{2,}[\s\-\.]?[0-9]{2,})",
        r"(?<!\w)(\+?[0-9]{1,4}[\s\-\.]?[0-9]{2,}[\s\-\.]?[0-9]{2,}[\s\-\.]?[0-9]{2,})(?!\w)"
    ]
    
    for pattern in phone_patterns:
        phone_match = re.search(pattern, message, re.IGNORECASE)
        if phone_match:
            # Nettoyer le numéro de téléphone (enlever espaces, tirets, points)
            phone = re.sub(r'[\s\-\.]', '', phone_match.group(1))
            data['phone_number'] = phone
            break
            
    # Extraction directe du numéro si c'est uniquement un numéro (comme un message isolé)
    if not data.get('phone_number'):
        phone_only_pattern = r"^[\s\-\.]?(\d+[\s\-\.]?\d+[\s\-\.]?\d+)[\s\-\.]?$"
        phone_only_match = re.search(phone_only_pattern, message.strip())
        if phone_only_match:
            phone = re.sub(r'[\s\-\.]', '', phone_only_match.group(1))
            data['phone_number'] = phone
    
    # Extraction du montant (commun aux deux types de transactions) - patrons élargis
    amount_patterns = [
        r"(\d+(?:[,.]\d+)?)\s*(?:euro|€|EUR)",
        r"(\d+(?:[,.]\d+)?)\s*(?:dinar|dinars|DT|TND)",
        r"montant\s+(?:de|est|:|s'élève à)?\s*(\d+(?:[,.]\d+)?)",
        r"(?:transférer|envoyer|transférer|recharger)(?:\s+(?:de|un montant de))?\s*(\d+(?:[,.]\d+)?)",
        r"(?<!\w)(\d+(?:[,.]\d+)?)(?:\s+(?:dinars?|euros?|DT|€|EUR|TND))(?!\w)",
        r"envoyer\s+(\d+(?:[,.]\d+)?)",
        r"virement\s+de\s+(\d+(?:[,.]\d+)?)"
    ]
    
    for pattern in amount_patterns:
        amount_match = re.search(pattern, message, re.IGNORECASE)
        if amount_match:
            # Convertir la virgule en point pour la valeur numérique
            amount = amount_match.group(1).replace(',', '.')
            try:
                # Vérifier que c'est bien un nombre
                float_amount = float(amount)
                if float_amount > 0:
                    data['amount'] = amount
                    break
            except ValueError:
                continue
    
    # Extraction de l'opérateur pour les recharges
    if transaction_type == 'recharge':
        operator_patterns = [
            r"(?:opérateur|fournisseur)\s+(?:est|:|s'appelle)?\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+|$|\.)",
            r"(?:chez|avec)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+|$|\.|,)",
            r"pour\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+(?:mobile|téléphone|portable))(?:\s+|$|\.)",
            r"(?:sim|carte|ligne)\s+(?:de|du)?\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+|$|\.|,)"
        ]
        
        # Liste des opérateurs courants pour validation
        known_operators = [
            "tunisie telecom", "orange tunisie", "ooredoo tunisie", 
            "orange", "ooredoo", "telecom", "maroc telecom", "orange maroc"
        ]
        
        for pattern in operator_patterns:
            operator_match = re.search(pattern, message, re.IGNORECASE)
            if operator_match:
                potential_operator = operator_match.group(1).strip().lower()
                # Vérifier si l'opérateur est connu
                for known_op in known_operators:
                    if known_op in potential_operator or potential_operator in known_op:
                        data['operator'] = potential_operator.title()  # Convertir en titre (première lettre en majuscule)
                        break
                if 'operator' in data:
                    break
        
        # Extraction directe si le message contient uniquement un nom d'opérateur
        if not data.get('operator') and len(message.strip().split()) <= 3:
            # Vérifier si le message entier correspond à un opérateur connu
            message_lower = message.lower().strip()
            for known_op in known_operators:
                if known_op in message_lower or message_lower in known_op:
                    data['operator'] = message_lower.title()
                    break
    
    print(f"Données extraites du message: {data}")
    return data

def extract_from_confirmation_message(message, transaction_type='transfer'):
    """
    Extrait les informations de transaction à partir du message de confirmation du chatbot.
    
    Args:
        message (str): Le message de l'assistant (chatbot)
        transaction_type (str): Le type de transaction ('transfer' ou 'recharge')
    
    Returns:
        dict: Les informations extraites
    """
    data = {}
    
    # Extraction du nom du bénéficiaire
    if transaction_type == 'transfer':
        recipient_pattern = r"Nom du bénéficiaire\s*:\s*([^\n:]+)"
        recipient_match = re.search(recipient_pattern, message, re.IGNORECASE)
        if recipient_match:
            data['recipient_name'] = recipient_match.group(1).strip()
        
        # Extraction de l'adresse
        address_pattern = r"Adresse\s*:\s*([^\n:]+)"
        address_match = re.search(address_pattern, message, re.IGNORECASE)
        if address_match:
            data['address'] = address_match.group(1).strip()
    
    # Extraction du numéro de téléphone (commun aux deux types)
    phone_pattern = r"(?:Numéro de téléphone|Téléphone)\s*:\s*([^\n:]+)"
    phone_match = re.search(phone_pattern, message, re.IGNORECASE)
    if phone_match:
        # Nettoyer le numéro de téléphone (enlever espaces, tirets, points)
        phone = re.sub(r'[\s\-\.]', '', phone_match.group(1))
        # Vérifier que le téléphone est un numéro valide
        if phone and phone.isdigit():
            data['phone_number'] = phone
        else:
            print(f"Numéro de téléphone invalide détecté: {phone}")
    
    # Extraction du montant (commun aux deux types)
    amount_pattern = r"Montant\s*:\s*(\d+(?:[,.]\d+)?)"
    amount_match = re.search(amount_pattern, message, re.IGNORECASE)
    if amount_match:
        # Convertir la virgule en point pour la valeur numérique
        amount = amount_match.group(1).replace(',', '.')
        try:
            # Vérifier que c'est bien un nombre
            float_amount = float(amount)
            if float_amount > 0:
                data['amount'] = amount
            else:
                print(f"Montant invalide détecté (doit être > 0): {float_amount}")
        except ValueError:
            print(f"Montant invalide détecté (non convertible en nombre): {amount_match.group(1)}")
    
    # Extraction de l'opérateur (seulement pour les recharges)
    if transaction_type == 'recharge':
        operator_pattern = r"Opérateur\s*:\s*([^\n:]+)"
        operator_match = re.search(operator_pattern, message, re.IGNORECASE)
        if operator_match:
            data['operator'] = operator_match.group(1).strip()
    
    # Vérifier si des champs sont vides ou manquants
    if transaction_type == 'transfer':
        required_fields = {
            'recipient_name': 'Nom du bénéficiaire',
            'address': 'Adresse', 
            'phone_number': 'Numéro de téléphone',
            'amount': 'Montant'
        }
    else:  # recharge
        required_fields = {
            'phone_number': 'Numéro de téléphone',
            'amount': 'Montant',
            'operator': 'Opérateur'
        }
    
    missing_fields = [field_name for field, field_name in required_fields.items() if field not in data]
    if missing_fields:
        print(f"ATTENTION: Champs manquants dans le message de confirmation: {', '.join(missing_fields)}")
    
    print(f"Données extraites du message de confirmation: {data}")
    return data

def update_transfer_data(existing_data, new_data):
    """
    Met à jour les données de transfert existantes avec les nouvelles données extraites.
    
    Args:
        existing_data (dict): Les données existantes
        new_data (dict): Les nouvelles données à fusionner
    
    Returns:
        dict: Les données mises à jour
    """
    result = existing_data.copy()
    
    # Ne mettre à jour que si la nouvelle valeur existe et n'est pas None
    for key, value in new_data.items():
        if value is not None:
            result[key] = value
    
    # Déterminer l'étape actuelle en fonction des champs renseignés
    transaction_type = result.get('transaction_type', 'transfer')
    
    if result.get('confirmed', False):
        result['step'] = 'completed'
    elif transaction_type == 'transfer' and all(result.get(field) for field in ['recipient_name', 'address', 'phone_number', 'amount']):
        result['step'] = 'confirmation'
    elif transaction_type == 'recharge' and all(result.get(field) for field in ['phone_number', 'amount', 'operator']):
        result['step'] = 'confirmation'
    elif result.get('step') == 'initial':
        result['step'] = 'in_progress'
    
    # Debug
    print(f"Données de transfert mises à jour: {result}")
    print(f"Étape actuelle: {result['step']}")
    
    return result

def process_conversation(request, chat_history, current_transfer_data, transaction_type='transfer'):
    """
    Traite la conversation pour détecter les confirmations et extraire les données de transaction.
    
    Args:
        request: La requête HTTP Django
        chat_history (list): L'historique de la conversation
        current_transfer_data (dict): Les données de transfert actuelles
        transaction_type (str): Le type de transaction ('transfer' ou 'recharge')
    
    Returns:
        tuple: (transaction_id, updated_transfer_data) - L'ID de transaction (si confirmée) et les données mises à jour
    """
    # S'assurer que nous avons un historique
    if not chat_history or len(chat_history) < 2:
        return None, current_transfer_data
    
    # Détecter une nouvelle transaction
    # Si le dernier message assistant contient un texte demandant toutes les informations de base,
    # c'est probablement une nouvelle transaction
    is_new_transaction = False
    
    for i in range(len(chat_history) - 1, 0, -1):
        if chat_history[i]['role'] == 'assistant':
            if "Pour cela, j'ai besoin de quelques informations" in chat_history[i]['content']:
                is_new_transaction = True
                break
    
    # Si une nouvelle transaction est détectée, réinitialiser les données
    if is_new_transaction:
        print("Nouvelle transaction détectée, réinitialisation des données")
        current_transfer_data = {
            'step': 'initial',
            'transaction_type': transaction_type,
            'confirmed': False,
            'completed': False
        }
    
    # Analyser les messages pour trouver le dernier message de confirmation COMPLET de l'assistant
    # Ce message doit contenir toutes les informations nécessaires à la transaction
    last_confirmation_message = None
    last_confirmation_index = -1
    
    for i in range(len(chat_history) - 1, 0, -1):
        if chat_history[i]['role'] == 'assistant':
            # Vérifier que le message contient bien "Est-ce correct ?" et les champs requis
            if "Est-ce correct ?" in chat_history[i]['content']:
                message = chat_history[i]['content']
                # Vérifier que tous les champs requis sont présents dans le message
                has_recipient = "Nom du bénéficiaire :" in message if transaction_type == 'transfer' else True
                has_address = "Adresse :" in message if transaction_type == 'transfer' else True
                has_phone = "Numéro de téléphone :" in message
                has_amount = "Montant :" in message
                has_operator = "Opérateur :" in message if transaction_type == 'recharge' else True
                
                if has_recipient and has_address and has_phone and has_amount and has_operator:
                    last_confirmation_message = message
                    last_confirmation_index = i
                    break
    
    # Ajouter le type de transaction aux données
    updated_data = current_transfer_data.copy()
    updated_data['transaction_type'] = transaction_type
    
    # Vérifier si un message de confirmation complet a été trouvé
    if last_confirmation_message and last_confirmation_index < len(chat_history) - 1:
        # Extraire d'abord les données du message de confirmation de l'assistant
        # pour vérifier que toutes les données requises sont présentes
        confirmation_data = extract_from_confirmation_message(last_confirmation_message, transaction_type)
        
        # Vérifier que toutes les données requises sont présentes dans le message de confirmation
        data_complete = False
        if transaction_type == 'transfer':
            required_fields = ['recipient_name', 'address', 'phone_number', 'amount']
            data_complete = all(confirmation_data.get(field) for field in required_fields)
        else:  # recharge
            required_fields = ['phone_number', 'amount', 'operator']
            data_complete = all(confirmation_data.get(field) for field in required_fields)
        
        # Seulement si les données sont complètes, vérifier la confirmation de l'utilisateur
        if data_complete:
            print("Message de confirmation complet détecté avec toutes les données requises")
            
            # Vérifier si le dernier message utilisateur après la confirmation est une confirmation
            user_responses_after_confirmation = [msg['content'] for msg in chat_history[last_confirmation_index+1:] if msg['role'] == 'user']
            
            if user_responses_after_confirmation:
                last_user_message = user_responses_after_confirmation[-1]
                is_confirmation = detect_confirmation(last_user_message)
                print(f"Le dernier message après confirmation est-il une confirmation? {is_confirmation}")
                
                if is_confirmation:
                    # Mettre à jour les données avec celles extraites du message de confirmation
                    updated_data = update_transfer_data(updated_data, confirmation_data)
                    
                    print("Confirmation utilisateur détectée avec données complètes!")
                    updated_data['confirmed'] = True
                    updated_data['completed'] = True
                    updated_data['step'] = 'completed'
                    
                    # Double vérification que toutes les données sont présentes
                    if transaction_type == 'transfer':
                        if not all(updated_data.get(field) for field in ['recipient_name', 'address', 'phone_number', 'amount']):
                            print("ERREUR: Certaines données sont manquantes malgré la confirmation!")
                            return None, updated_data
                    else:  # recharge
                        if not all(updated_data.get(field) for field in ['phone_number', 'amount', 'operator']):
                            print("ERREUR: Certaines données sont manquantes malgré la confirmation!")
                            return None, updated_data
                    
                    # Enregistrer la transaction
                    try:
                        transaction_id = save_transaction(request.user.username, updated_data, transaction_type)
                        print(f"Transaction enregistrée avec ID: {transaction_id}")
                        return transaction_id, updated_data
                    except Exception as e:
                        print(f"Erreur lors de l'enregistrement de la transaction: {str(e)}")
                        import traceback
                        print(traceback.format_exc())
    
    # Si pas de confirmation ou données incomplètes, continuer avec l'extraction normale
    # Trouver l'index du dernier assistant qui demande les informations de base
    last_init_index = 0
    for i in range(len(chat_history) - 1, 0, -1):
        if chat_history[i]['role'] == 'assistant':
            if "Pour cela, j'ai besoin de quelques informations" in chat_history[i]['content']:
                last_init_index = i
                break
    
    # Utiliser uniquement les messages depuis cette demande initiale
    relevant_messages = chat_history[last_init_index:]
    user_messages = [msg['content'] for msg in relevant_messages if msg['role'] == 'user']
    
    if not user_messages:
        return None, updated_data
    
    # Logging
    print(f"Traitement de {len(user_messages)} messages utilisateur pertinents")
    
    # Extraire les données de tous les messages récents
    for message in user_messages:
        print(f"Analyse du message: '{message}'")
        extracted_data = extract_transaction_data(message, transaction_type)
        updated_data = update_transfer_data(updated_data, extracted_data)
    
    return None, updated_data

def save_transaction(user_id, transfer_data, transaction_type):
    """
    Enregistre les données de transaction dans un fichier JSON.
    
    Args:
        user_id (str): L'identifiant de l'utilisateur
        transfer_data (dict): Les données de transfert
        transaction_type (str): Le type de transaction ('transfer' ou 'recharge')
    
    Returns:
        str: L'identifiant de la transaction
    """
    # Créer le répertoire de transactions s'il n'existe pas
    transactions_dir = os.path.join(settings.MEDIA_ROOT, 'transactions')
    os.makedirs(transactions_dir, exist_ok=True)
    
    # Debug: Vérifier que le répertoire existe bien
    print(f"Création/vérification du répertoire transactions: {transactions_dir}")
    print(f"Le répertoire existe: {os.path.exists(transactions_dir)}")
    
    # Générer un identifiant unique pour la transaction
    transaction_id = f"{transaction_type}_{uuid.uuid4().hex[:8]}"
    
    # Préparer les données à sauvegarder
    transaction_data = {
        'transaction_id': transaction_id,
        'user_id': user_id,
        'transaction_type': transaction_type,
        'timestamp': datetime.now().isoformat(),
        'status': 'completed' if transfer_data.get('confirmed', False) else 'pending',
    }
    
    # Ajouter les données spécifiques au type de transaction
    if transaction_type == 'transfer':
        transaction_data.update({
            'recipient_name': transfer_data.get('recipient_name', ''),
            'address': transfer_data.get('address', ''),
            'phone_number': transfer_data.get('phone_number', ''),
            'amount': float(transfer_data.get('amount', 0)) if transfer_data.get('amount') else 0,
            'currency': 'TND'  # Dinar tunisien par défaut
        })
    else:  # recharge
        transaction_data.update({
            'phone_number': transfer_data.get('phone_number', ''),
            'amount': float(transfer_data.get('amount', 0)) if transfer_data.get('amount') else 0,
            'operator': transfer_data.get('operator', ''),  # Utiliser l'opérateur fourni par l'utilisateur
            'currency': 'TND'  # Dinar tunisien par défaut
        })
    
    # Debug: Afficher les données à sauvegarder
    print(f"Données de transaction à sauvegarder: {transaction_data}")
    
    # Sauvegarder dans un fichier JSON
    file_path = os.path.join(transactions_dir, f"{transaction_id}.json")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(transaction_data, f, ensure_ascii=False, indent=4)
        print(f"Transaction sauvegardée avec succès dans: {file_path}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la transaction: {str(e)}")
    
    return transaction_id