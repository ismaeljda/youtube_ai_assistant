# multi_agent.py - Système Multi-Agents avec LangChain
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_community.callbacks.manager import get_openai_callback
from typing import Dict, List, Any, Tuple
import json
import re
from datetime import datetime
from pydantic import BaseModel

class MultiAgentYouTubeAssistant:
    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        """
        Initialise le système multi-agents
        
        Args:
            api_key: Clé API OpenAI
            model_name: Modèle à utiliser (gpt-4, gpt-3.5-turbo, etc.)
        """
        self.api_key = api_key
        self.llm = ChatOpenAI(
            openai_api_key=api_key,
            model_name=model_name,
            temperature=0.1,  # Faible température pour l'agent analyseur
            max_tokens=2000
        )
        
        # LLM pour l'agent répondeur (plus créatif)
        self.response_llm = ChatOpenAI(
            openai_api_key=api_key,
            model_name=model_name,
            temperature=0.7,
            max_tokens=1500
        )
        
        self.setup_agents()
    
    def setup_agents(self):
        """Configure les prompts des deux agents"""
        
        # Agent 1: Analyseur de questions
        self.analyzer_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("""
Tu es un expert en analyse de questions sur du contenu vidéo YouTube.
Ton rôle est d'analyser précisément la question de l'utilisateur et de déterminer:

1. **TYPE DE QUESTION** (choisis UN seul type):
   - "definition": L'utilisateur demande une définition ou explication d'un concept
   - "clarification": L'utilisateur veut clarifier quelque chose qui vient d'être dit
   - "context": L'utilisateur veut du contexte ou des détails supplémentaires
   - "summary": L'utilisateur veut un résumé de ce qui a été dit
   - "timestamp": L'utilisateur fait référence à un moment spécifique
   - "comparison": L'utilisateur veut comparer des éléments
   - "application": L'utilisateur veut savoir comment appliquer quelque chose
   - "general": Question générale sur le sujet de la vidéo

2. **STRATÉGIE DE CONTEXTE** (choisis UNE stratégie):
   - "current_focus": Se concentrer principalement sur le moment actuel
   - "recent_context": Utiliser les 2-3 dernières minutes
   - "broad_context": Chercher dans toute la vidéo
   - "specific_search": Chercher des mots-clés spécifiques

3. **STYLE DE RÉPONSE** (choisis UN style):
   - "concise": Réponse courte et directe
   - "detailed": Explication détaillée avec exemples
   - "step_by_step": Explication étape par étape
   - "conversational": Ton naturel et accessible

4. **MOTS-CLÉS IMPORTANTS**: Extrais les termes clés de la question

Réponds UNIQUEMENT en format JSON valide:
{
    "question_type": "...",
    "context_strategy": "...",
    "response_style": "...",
    "keywords": ["mot1", "mot2", ...],
    "confidence": 0.95,
    "reasoning": "Courte explication de ton analyse"
}
"""),
            HumanMessagePromptTemplate.from_template("""
QUESTION DE L'UTILISATEUR: "{user_question}"

MOMENT ACTUEL DANS LA VIDÉO: {current_time_formatted}

CONTEXTE AUTOUR DU MOMENT ACTUEL:
{priority_context_preview}

Analyse cette question et réponds en JSON:
""")
        ])
        
        # Agent 2: Générateur de réponses
        self.responder_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("""
Tu es un assistant IA expert en explication de contenu vidéo YouTube.
Tu reçois une analyse détaillée de la question utilisateur et tu dois générer la meilleure réponse possible.

DIRECTIVES SELON LE TYPE DE QUESTION:

**DEFINITION**: Donne une définition claire, puis explique dans le contexte de la vidéo
**CLARIFICATION**: Éclaircis le point confus en te basant sur ce qui vient d'être dit
**CONTEXT**: Fournis le contexte manquant, connecte avec d'autres parties de la vidéo
**SUMMARY**: Résume de façon structurée et claire
**TIMESTAMP**: Fais référence aux moments précis avec les timestamps
**COMPARISON**: Compare les éléments en soulignant les différences/similitudes
**APPLICATION**: Donne des exemples concrets d'application
**GENERAL**: Réponds de façon générale mais en restant ancré dans le contenu vidéo

DIRECTIVES SELON LE STYLE:

**CONCISE**: Réponse en 2-3 phrases maximum
**DETAILED**: Explication complète avec exemples du contexte vidéo
**STEP_BY_STEP**: Structure en étapes numérotées ou à puces
**CONVERSATIONAL**: Ton naturel, comme si tu expliquais à un ami

RÈGLES IMPORTANTES:
- Utilise les timestamps [MM:SS] quand tu fais référence à d'autres moments
- Reste fidèle au contenu de la vidéo
- Si l'info n'est pas dans le contexte fourni, dis-le clairement
- Sois précis et évite les généralités
"""),
            HumanMessagePromptTemplate.from_template("""
QUESTION ORIGINALE: "{original_question}"

ANALYSE DE LA QUESTION:
- Type: {question_type}
- Stratégie de contexte: {context_strategy}  
- Style de réponse: {response_style}
- Mots-clés: {keywords}

MOMENT ACTUEL: {current_time_formatted}

CONTEXTE PRIORITAIRE (autour du moment actuel):
{priority_context}

CONTEXTE DE RÉFÉRENCE (reste de la vidéo):
{extended_context}

Génère maintenant une réponse optimale selon l'analyse fournie:
""")
        ])
    
    def analyze_question(self, user_question: str, contextual_data: Dict) -> Dict:
        """
        Agent 1: Analyse la question de l'utilisateur
        """
        try:
            # Créer un aperçu du contexte prioritaire pour l'analyseur
            priority_preview = (
                contextual_data['priority_window_text'][:300] + "..."
                if len(contextual_data['priority_window_text']) > 300
                else contextual_data['priority_window_text']
            )

            # Formatage du prompt pour l'analyseur
            analyzer_messages = self.analyzer_prompt.format_messages(
                user_question=user_question,
                current_time_formatted=contextual_data['current_time_formatted'],
                priority_context_preview=priority_preview
            )

            # Appel à l'agent analyseur avec invoke()
            with get_openai_callback() as cb:
                analysis_response = self.llm.invoke(analyzer_messages)
                print(f"💰 Coût Agent Analyseur: ${cb.total_cost:.4f}")

            # Récupérer le texte brut
            analysis_text = analysis_response.content.strip()

            # Essayer d'extraire du JSON
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                candidate = json_match.group(0)
            else:
                # Si pas d'accolades, on essaie de forcer
                candidate = "{" + analysis_text + "}"

            # Nettoyage basique
            candidate = candidate.replace("'", '"').replace("\n", " ").strip()

            try:
                analysis_json = json.loads(candidate)
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON mal formé même après nettoyage ({e}), fallback utilisé")
                analysis_json = {
                    "question_type": "general",
                    "context_strategy": "current_focus",
                    "response_style": "conversational",
                    "keywords": [],
                    "confidence": 0.4,
                    "reasoning": f"Parsing failed: {str(e)}"
                }

            print(f"🔍 Analyse terminée: "
                f"{analysis_json.get('question_type', 'general')} | "
                f"{analysis_json.get('context_strategy', 'current_focus')} | "
                f"{analysis_json.get('response_style', 'conversational')}")
            return analysis_json

        except Exception as e:
            print(f"❌ Erreur dans analyze_question: {e}")
            # Analyse par défaut
            return {
                "question_type": "general",
                "context_strategy": "current_focus",
                "response_style": "conversational",
                "keywords": [],
                "confidence": 0.3,
                "reasoning": f"Error fallback: {str(e)}"
            }

    def generate_response(self, original_question: str, analysis: Dict, contextual_data: Dict) -> str:
        """
        Agent 2: Génère la réponse basée sur l'analyse
        """
        try:
            # Ajuster le contexte selon la stratégie analysée
            context_data = self.adjust_context_by_strategy(contextual_data, analysis)
            
            # Formatage du prompt pour le générateur de réponses
            responder_messages = self.responder_prompt.format_messages(
                original_question=original_question,
                question_type=analysis['question_type'],
                context_strategy=analysis['context_strategy'],
                response_style=analysis['response_style'],
                keywords=', '.join(analysis.get('keywords', [])),
                current_time_formatted=contextual_data['current_time_formatted'],
                priority_context=context_data['priority_context'],
                extended_context=context_data['extended_context']
            )
            
            # Appel à l'agent répondeur
            with get_openai_callback() as cb:
                response = self.llm.invoke(responder_messages)
                print(f"💰 Coût Agent Répondeur: ${cb.total_cost:.4f}")
            
            return response.content.strip()
            
        except Exception as e:
            print(f"❌ Erreur dans generate_response: {e}")
            return f"Désolé, une erreur est survenue lors de la génération de la réponse: {str(e)}"
    
    def adjust_context_by_strategy(self, contextual_data: Dict, analysis: Dict) -> Dict:
        """
        Ajuste le contexte fourni selon la stratégie déterminée par l'analyseur
        """
        strategy = analysis['context_strategy']
        
        if strategy == "current_focus":
            # Se concentrer sur le moment actuel seulement
            return {
                'priority_context': contextual_data['priority_window_text'],
                'extended_context': contextual_data['extended_context_summary'][:500] + "..."
            }
            
        elif strategy == "recent_context":
            # Contexte récent plus large
            return {
                'priority_context': contextual_data['priority_window_text'],
                'extended_context': contextual_data['extended_context_summary'][:800] + "..."
            }
            
        elif strategy == "broad_context":
            # Utiliser tout le contexte disponible
            return {
                'priority_context': contextual_data['priority_window_text'],
                'extended_context': contextual_data['extended_context_summary']
            }
            
        elif strategy == "specific_search":
            # Rechercher des mots-clés spécifiques (implémentation simplifiée)
            keywords = analysis.get('keywords', [])
            filtered_context = self.filter_context_by_keywords(
                contextual_data['extended_context_summary'], 
                keywords
            )
            return {
                'priority_context': contextual_data['priority_window_text'],
                'extended_context': filtered_context
            }
        
        # Défaut
        return {
            'priority_context': contextual_data['priority_window_text'],
            'extended_context': contextual_data['extended_context_summary']
        }
    
    def filter_context_by_keywords(self, context: str, keywords: List[str]) -> str:
        """
        Filtre le contexte pour ne garder que les sections contenant les mots-clés
        """
        if not keywords:
            return context
        
        # Diviser le contexte en paragraphes
        paragraphs = context.split('\n\n')
        relevant_paragraphs = []
        
        for paragraph in paragraphs:
            # Vérifier si le paragraphe contient au moins un mot-clé
            paragraph_lower = paragraph.lower()
            if any(keyword.lower() in paragraph_lower for keyword in keywords):
                relevant_paragraphs.append(paragraph)
        
        return '\n\n'.join(relevant_paragraphs) if relevant_paragraphs else context[:1000] + "..."
    
    def process_question(self, user_question: str, contextual_data: Dict) -> Dict:
        """
        Pipeline complet: Analyse + Génération de réponse
        
        Returns:
            Dict contenant la réponse et les métadonnées de l'analyse
        """
        print(f"🚀 Début du traitement multi-agents")
        print(f"📝 Question: {user_question}")
        print(f"⏰ Moment: {contextual_data['current_time_formatted']}")
        
        # Étape 1: Analyse de la question
        analysis = self.analyze_question(user_question, contextual_data)
        
        # Étape 2: Génération de la réponse
        response = self.generate_response(user_question, analysis, contextual_data)
        
        # Retourner les résultats complets
        return {
            'response': response,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'context_used': len(contextual_data['priority_context'])
        }

# Fonction utilitaire pour tester le système
def test_multi_agent_system():
    """
    Test rapide du système multi-agents
    """
    # Configuration de test
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY non trouvée dans .env")
        return
    
    # Initialiser le système
    assistant = MultiAgentYouTubeAssistant(api_key)
    
    # Données de test
    test_contextual_data = {
        'current_time_formatted': '15:30',
        'priority_window_text': '[15:20] Nous allons maintenant parler des algorithmes de tri. [15:25] Le tri à bulles est l\'un des plus simples à comprendre. [15:30] Il compare chaque élément avec son voisin.',
        'extended_context_summary': '[10:00] Introduction aux algorithmes...\n[12:00] Les structures de données...',
        'priority_context': []
    }
    
    # Test
    result = assistant.process_question(
        "Qu'est-ce que le tri à bulles ?", 
        test_contextual_data
    )
    
    print(f"\n✅ Résultat du test:")
    print(f"Type de question: {result['analysis']['question_type']}")
    print(f"Stratégie: {result['analysis']['context_strategy']}")
    print(f"Style: {result['analysis']['response_style']}")
    print(f"Réponse: {result['response']}")

if __name__ == "__main__":
    test_multi_agent_system()