from youtube_transcript_api import YouTubeTranscriptApi
from typing import List, Dict, Tuple
from openai import OpenAI  # Nouvelle version OpenAI

class ContextualTranscriptProcessor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        
    def get_transcript(self, video_id: str) -> List[Dict]:
        """Récupère le transcript d'une vidéo YouTube"""
        try:
            # Utiliser directement api.fetch qui fonctionne dans votre cas
            api = YouTubeTranscriptApi()
            transcript_obj = api.fetch(video_id)
            segments_data = []
            
            print(f"Debug: Type d'objet transcript: {type(transcript_obj)}")
            
            if hasattr(transcript_obj, 'segments'):
                for segment in transcript_obj.segments:
                    segments_data.append({
                        'start': segment.start,
                        'duration': segment.duration if hasattr(segment, 'duration') else 0,
                        'text': segment.text
                    })
            elif hasattr(transcript_obj, 'entries'):
                for entry in transcript_obj.entries:
                    segments_data.append({
                        'start': entry.start,
                        'duration': entry.duration if hasattr(entry, 'duration') else 0,
                        'text': entry.text
                    })
            elif hasattr(transcript_obj, 'snippets'):
                for snippet in transcript_obj.snippets:
                    segments_data.append({
                        'start': snippet.start,
                        'duration': snippet.duration if hasattr(snippet, 'duration') else 0,
                        'text': snippet.text
                    })
            else:
                print("Structure de transcript non reconnue:", type(transcript_obj))
                print("Attributs disponibles:", [attr for attr in dir(transcript_obj) if not attr.startswith('_')])
                return []
            
            print(f"✅ Transcript récupéré: {len(segments_data)} segments")
            return segments_data
            
        except Exception as e:
            print(f"Erreur récupération transcript: {e}")
            return []
    
    
    def create_contextual_windows(self, transcript: List[Dict], current_time: float, 
                                priority_window: int = 120, extended_window: int = 30) -> Dict:
        """
        Crée les fenêtres de contexte prioritaire et étendu
        
        Args:
            transcript: Liste des segments du transcript
            current_time: Moment actuel dans la vidéo (en secondes)
            priority_window: Taille de la fenêtre prioritaire en secondes (avant)
            extended_window: Taille de la fenêtre prioritaire en secondes (après)
        """
        priority_context = []
        extended_context = []
        
        start_priority = max(0, current_time - priority_window)
        end_priority = current_time + extended_window
        
        for segment in transcript:
            segment_start = segment['start']
            segment_end = segment['start'] + segment['duration']
            
            # Contexte prioritaire (fenêtre autour du moment actuel)
            if start_priority <= segment_start <= end_priority:
                priority_context.append({
                    'start': segment_start,
                    'end': segment_end,
                    'text': segment['text'],
                    'timestamp_formatted': self.format_timestamp(segment_start)
                })
            
            # Contexte étendu (tout le reste)
            else:
                extended_context.append({
                    'start': segment_start,
                    'end': segment_end,
                    'text': segment['text'],
                    'timestamp_formatted': self.format_timestamp(segment_start)
                })
        
        return {
            'current_time': current_time,
            'current_time_formatted': self.format_timestamp(current_time),
            'priority_context': priority_context,
            'extended_context': extended_context,
            'priority_window_text': self.concatenate_segments(priority_context),
            'extended_context_summary': self.summarize_extended_context(extended_context)
        }
    
    def format_timestamp(self, seconds: float) -> str:
        """Formate les secondes en MM:SS"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def concatenate_segments(self, segments: List[Dict]) -> str:
        """Concatène les segments avec leurs timestamps"""
        result = ""
        for segment in segments:
            result += f"[{segment['timestamp_formatted']}] {segment['text']}\n"
        return result
    
    def summarize_extended_context(self, extended_context: List[Dict]) -> str:
        """
        Crée un résumé structuré du contexte étendu
        Groupe par sections de 5 minutes pour une meilleure lisibilité
        """
        if not extended_context:
            return ""
        
        # Grouper par tranches de 5 minutes
        sections = {}
        for segment in extended_context:
            section_key = int(segment['start'] // 300) * 5  # Tranches de 5 minutes
            if section_key not in sections:
                sections[section_key] = []
            sections[section_key].append(segment)
        
        summary = ""
        for section_start, segments in sorted(sections.items()):
            section_end = section_start + 5
            section_text = " ".join([s['text'] for s in segments])
            summary += f"[{section_start:02d}:00-{section_end:02d}:00] {section_text[:200]}...\n\n"
        
        return summary
    
    def build_ai_prompt(self, contextual_data: Dict, user_question: str) -> str:
        """Construit le prompt structuré pour l'IA"""
        
        prompt = f"""Tu es un assistant IA spécialisé dans l'aide à la compréhension de vidéos YouTube.

L'utilisateur regarde une vidéo et se trouve actuellement à {contextual_data['current_time_formatted']} dans la vidéo.

=== CONTEXTE PRIORITAIRE (autour du moment actuel {contextual_data['current_time_formatted']}) ===
{contextual_data['priority_window_text']}

=== CONTEXTE DE RÉFÉRENCE (reste de la vidéo) ===
{contextual_data['extended_context_summary']}

=== QUESTION DE L'UTILISATEUR ===
"{user_question}"

=== INSTRUCTIONS ===
1. Réponds en utilisant PRIORITAIREMENT le contexte autour du moment actuel
2. Utilise le contexte de référence pour les définitions, rappels ou connexions nécessaires
3. Si tu fais référence à un autre moment de la vidéo, indique le timestamp
4. Sois précis et contextualisé à ce moment exact de la vidéo
5. Si la réponse n'est pas dans le contexte prioritaire, cherche dans le contexte de référence

Réponse:"""
        
        return prompt
    
    def ask_question(self, video_id: str, current_time: float, question: str) -> str:
        """
        Pipeline complet: récupère transcript, crée contexte, pose question à l'IA
        """
        # 1. Récupérer le transcript
        transcript = self.get_transcript(video_id)
        if not transcript:
            return "Impossible de récupérer le transcript de cette vidéo."
        
        # 2. Créer les fenêtres contextuelles
        contextual_data = self.create_contextual_windows(transcript, current_time)
        
        # 3. Construire le prompt
        prompt = self.build_ai_prompt(contextual_data, question)
        
        # 4. Interroger l'IA
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Tu es un assistant IA spécialisé dans l'explication de contenu vidéo."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Erreur lors de la génération de la réponse: {e}"
