# memory_system.py - Système de mémoire pour l'assistant
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

class ConversationMemory:
    def __init__(self, max_messages: int = 10, session_timeout: int = 1800):  # 30 minutes
        """
        Système de mémoire pour les conversations
        
        Args:
            max_messages: Nombre maximum de messages à retenir par session
            session_timeout: Timeout de session en secondes
        """
        self.sessions = {}  # video_id -> conversation_data
        self.max_messages = max_messages
        self.session_timeout = session_timeout
    
    def get_session_key(self, video_id: str, user_id: str = "default") -> str:
        """Génère une clé de session unique"""
        return f"{video_id}_{user_id}"
    
    def add_message(self, video_id: str, question: str, response: str, 
                   timestamp: float, user_id: str = "default") -> None:
        """Ajoute un message à l'historique"""
        session_key = self.get_session_key(video_id, user_id)
        current_time = datetime.now()
        
        if session_key not in self.sessions:
            self.sessions[session_key] = {
                'video_id': video_id,
                'user_id': user_id,
                'created_at': current_time,
                'last_activity': current_time,
                'messages': []
            }
        
        # Ajouter le nouveau message
        self.sessions[session_key]['messages'].append({
            'question': question,
            'response': response,
            'timestamp': timestamp,
            'time_formatted': self.format_timestamp(timestamp),
            'created_at': current_time
        })
        
        # Mettre à jour la dernière activité
        self.sessions[session_key]['last_activity'] = current_time
        
        # Limiter le nombre de messages
        if len(self.sessions[session_key]['messages']) > self.max_messages:
            self.sessions[session_key]['messages'] = self.sessions[session_key]['messages'][-self.max_messages:]
    
    def get_conversation_history(self, video_id: str, user_id: str = "default") -> List[Dict]:
        """Récupère l'historique de conversation pour une session"""
        session_key = self.get_session_key(video_id, user_id)
        
        if session_key not in self.sessions:
            return []
        
        # Vérifier si la session n'a pas expiré
        session = self.sessions[session_key]
        time_since_last_activity = datetime.now() - session['last_activity']
        
        if time_since_last_activity.total_seconds() > self.session_timeout:
            # Session expirée, la supprimer
            del self.sessions[session_key]
            return []
        
        return session['messages']
    
    def get_conversation_context(self, video_id: str, user_id: str = "default") -> str:
        """Génère un contexte textuel de la conversation pour l'IA"""
        history = self.get_conversation_history(video_id, user_id)
        
        if not history:
            return ""
        
        context = "=== HISTORIQUE DE CONVERSATION ===\n"
        for i, msg in enumerate(history, 1):
            context += f"\n[{msg['time_formatted']}] Question {i}: {msg['question']}\n"
            context += f"[{msg['time_formatted']}] Réponse {i}: {msg['response'][:150]}...\n"
        
        context += "\n=== FIN HISTORIQUE ===\n"
        return context
    
    def clear_session(self, video_id: str, user_id: str = "default") -> None:
        """Efface une session spécifique"""
        session_key = self.get_session_key(video_id, user_id)
        if session_key in self.sessions:
            del self.sessions[session_key]
    
    def cleanup_expired_sessions(self) -> int:
        """Nettoie les sessions expirées"""
        current_time = datetime.now()
        expired_keys = []
        
        for session_key, session in self.sessions.items():
            time_since_last_activity = current_time - session['last_activity']
            if time_since_last_activity.total_seconds() > self.session_timeout:
                expired_keys.append(session_key)
        
        for key in expired_keys:
            del self.sessions[key]
        
        return len(expired_keys)
    
    def format_timestamp(self, seconds: float) -> str:
        """Formate les secondes en MM:SS"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_stats(self) -> Dict:
        """Statistiques du système de mémoire"""
        return {
            'active_sessions': len(self.sessions),
            'total_messages': sum(len(session['messages']) for session in self.sessions.values()),
            'oldest_session': min([session['created_at'] for session in self.sessions.values()]) if self.sessions else None
        }

# Classe mise à jour du processeur contextuel avec mémoire
class ContextualTranscriptProcessorWithMemory:
    def __init__(self, api_key: str):
        from openai import OpenAI
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.memory = ConversationMemory()
        
        # Import du processeur original pour récupérer les transcripts
        from contextual_transcript_processor import ContextualTranscriptProcessor
        self.transcript_processor = ContextualTranscriptProcessor(api_key)
    
    def ask_question_with_memory(self, video_id: str, current_time: float, 
                                question: str, user_id: str = "default") -> Dict:
        """
        Pose une question en tenant compte de l'historique de conversation
        """
        # 1. Récupérer l'historique de conversation
        conversation_context = self.memory.get_conversation_context(video_id, user_id)
        
        # 2. Récupérer le transcript et créer le contexte
        transcript = self.transcript_processor.get_transcript(video_id)
        if not transcript:
            return {"error": "Impossible de récupérer le transcript de cette vidéo."}
        
        contextual_data = self.transcript_processor.create_contextual_windows(transcript, current_time)
        
        # 3. Construire le prompt avec mémoire
        prompt = self.build_ai_prompt_with_memory(contextual_data, question, conversation_context)
        
        # 4. Interroger l'IA
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Tu es un assistant IA spécialisé dans l'explication de contenu vidéo avec mémoire des conversations précédentes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # 5. Sauvegarder dans la mémoire
            self.memory.add_message(video_id, question, ai_response, current_time, user_id)
            
            return {
                "response": ai_response,
                "has_conversation_history": bool(conversation_context),
                "conversation_length": len(self.memory.get_conversation_history(video_id, user_id))
            }
            
        except Exception as e:
            return {"error": f"Erreur lors de la génération de la réponse: {e}"}
    
    def build_ai_prompt_with_memory(self, contextual_data: Dict, user_question: str, 
                                   conversation_context: str) -> str:
        """Construit le prompt avec le contexte de conversation"""
        
        memory_instruction = ""
        if conversation_context:
            memory_instruction = f"""
{conversation_context}

INSTRUCTIONS MÉMOIRE:
- Tu as accès à l'historique de cette conversation sur cette vidéo
- Fais référence aux questions/réponses précédentes si c'est pertinent
- Si l'utilisateur dit "comme tu l'as dit avant" ou fait référence à une réponse précédente, utilise l'historique
- Maintiens la cohérence avec tes réponses précédentes
"""
        
        prompt = f"""Tu es un assistant IA spécialisé dans l'aide à la compréhension de vidéos YouTube.

L'utilisateur regarde une vidéo et se trouve actuellement à {contextual_data['current_time_formatted']} dans la vidéo.

{memory_instruction}

=== CONTEXTE PRIORITAIRE (autour du moment actuel {contextual_data['current_time_formatted']}) ===
{contextual_data['priority_window_text']}

=== CONTEXTE DE RÉFÉRENCE (reste de la vidéo) ===
{contextual_data['extended_context_summary']}

=== QUESTION ACTUELLE DE L'UTILISATEUR ===
"{user_question}"

=== INSTRUCTIONS ===
1. Réponds en utilisant PRIORITAIREMENT le contexte autour du moment actuel
2. Utilise le contexte de référence pour les définitions, rappels ou connexions nécessaires
3. Si tu fais référence à un autre moment de la vidéo, indique le timestamp
4. Utilise l'historique de conversation si la question fait référence à des échanges précédents
5. Sois précis et contextualisé à ce moment exact de la vidéo

Réponse:"""
        
        return prompt
    
    def clear_conversation(self, video_id: str, user_id: str = "default"):
        """Efface l'historique de conversation pour une vidéo"""
        self.memory.clear_session(video_id, user_id)
    
    def get_conversation_stats(self) -> Dict:
        """Statistiques de mémoire"""
        return self.memory.get_stats()

# Fonction utilitaire pour tester le système de mémoire
def test_memory_system():
    """Test du système de mémoire"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY non trouvée")
        return
    
    processor = ContextualTranscriptProcessorWithMemory(api_key)
    
    # Simuler une conversation
    video_id = "SmZmBKc7Lrs"
    
    print("🧠 Test du système de mémoire")
    
    # Première question
    result1 = processor.ask_question_with_memory(video_id, 120, "Qu'est-ce qu'un algorithme ?")
    print(f"Q1: Historique = {result1.get('has_conversation_history', False)}")
    
    # Deuxième question (devrait avoir la mémoire de la première)
    result2 = processor.ask_question_with_memory(video_id, 150, "Comme tu l'as dit avant, peux-tu donner un exemple ?")
    print(f"Q2: Historique = {result2.get('has_conversation_history', False)}")
    print(f"Longueur conversation = {result2.get('conversation_length', 0)}")
    
    # Stats
    stats = processor.get_conversation_stats()
    print(f"📊 Stats: {stats}")

if __name__ == "__main__":
    test_memory_system()