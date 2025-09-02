# app.py - Backend Flask avec système Multi-Agents
from flask import Flask, request, jsonify
from flask_cors import CORS
from contextual_transcript_processor import ContextualTranscriptProcessor
from multi_agents import MultiAgentYouTubeAssistant
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)  # Permettre les requêtes depuis l'extension

# Initialiser les deux systèmes
API_KEY = os.getenv('OPENAI_API_KEY', 'api_key')

# Système multi-agents (principal)
multi_agent_assistant = MultiAgentYouTubeAssistant(API_KEY)

# Processeur contextuel (pour récupérer les transcripts)
transcript_processor = ContextualTranscriptProcessor(API_KEY)

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        # Debug des informations de la requête
        print(f"📨 Requête reçue: {request.method}")
        print(f"📋 Headers: {dict(request.headers)}")
        print(f"📦 Raw data: {request.get_data()}")

        # Récupération des données JSON
        data = request.get_json(force=True, silent=True) or {}
        print(f"🔍 Data parsée: {data}")

        # Extraction des paramètres
        video_id = data.get("video_id")
        current_time = data.get("current_time", 0)
        question = data.get("question")

        print("✅ Paramètres extraits:")
        print(f"   - video_id: '{video_id}' (type: {type(video_id)})")
        print(f"   - current_time: {current_time} (type: {type(current_time)})")
        print(f"   - question: '{question}' (type: {type(question)})")

        # Validation
        if not video_id or not question:
            print(f"❌ Validation échouée: video_id='{video_id}', question='{question}'")
            return jsonify({
                "error": "video_id et question sont requis",
                "received_video_id": video_id,
                "received_question": question
            }), 400

        # 1. Récupérer le transcript via le processeur contextuel
        transcript = transcript_processor.get_transcript(video_id)
        if not transcript:
            return jsonify({
                "error": "Impossible de récupérer le transcript de cette vidéo",
                "video_id": video_id
            }), 404

        # 2. Créer les fenêtres contextuelles
        contextual_data = transcript_processor.create_contextual_windows(transcript, current_time)

        # 3. Traitement via le système multi-agents
        result = multi_agent_assistant.process_question(question, contextual_data)

        # Log de l'analyse
        print("✅ Analyse multi-agents terminée:")
        print(f"   - Type de question: {result['analysis'].get('question_type', 'unknown')}")
        print(f"   - Stratégie: {result['analysis'].get('context_strategy', 'unknown')}")
        print(f"   - Style: {result['analysis'].get('response_style', 'unknown')}")
        print(f"   - Confiance: {result['analysis'].get('confidence', 0)}")
        print(f"   - Contexte utilisé: {result.get('context_used', 0)} segments")

        return jsonify({
            "response": result.get("response", ""),
            "video_id": video_id,
            "timestamp": current_time,
            "analysis": {
                "question_type": result["analysis"].get("question_type", "unknown"),
                "strategy": result["analysis"].get("context_strategy", "unknown"),
                "style": result["analysis"].get("response_style", "unknown"),
                "confidence": result["analysis"].get("confidence", 0),
                "keywords": result["analysis"].get("keywords", []),
                "reasoning": result["analysis"].get("reasoning", "")
            },
            "metadata": {
                "timestamp": result.get("timestamp", ""),
                "context_segments": result.get("context_used", 0),
                "processing_time": result.get("processing_time", "N/A")
            },
            "debug_info": f"Multi-agent: {result['analysis'].get('question_type', 'unknown')} question processed with {result['analysis'].get('context_strategy', 'unknown')} strategy"
        })

    except Exception as e:
        print(f"🚨 Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Erreur interne du serveur",
            "details": str(e)
        }), 500


@app.route('/ask/simple', methods=['POST'])
def ask_question_simple():
    """
    Endpoint alternatif utilisant l'ancien système (pour comparaison)
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        video_id = data.get("video_id")
        current_time = data.get("current_time", 0)
        question = data.get("question")

        if not video_id or not question:
            return jsonify({
                "error": "video_id et question sont requis"
            }), 400

        # Utiliser l'ancien système contextuel simple
        result = transcript_processor.ask_question(video_id, current_time, question)

        return jsonify({
            "response": result,
            "video_id": video_id,
            "timestamp": current_time,
            "system": "simple_contextual"
        })

    except Exception as e:
        print(f"🚨 Erreur simple: {e}")
        return jsonify({
            "error": "Erreur interne du serveur",
            "details": str(e)
        }), 500


@app.route('/transcript/<video_id>', methods=['GET'])
def get_transcript_info(video_id):
    """Endpoint pour récupérer des infos sur le transcript"""
    try:
        transcript = transcript_processor.get_transcript(video_id)
        
        if not transcript:
            return jsonify({
                'error': 'Transcript non disponible'
            }), 404
        
        return jsonify({
            'video_id': video_id,
            'segments_count': len(transcript),
            'duration': transcript[-1]['start'] if transcript else 0,
            'available': True
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Erreur lors de la récupération du transcript',
            'details': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de santé"""
    return jsonify({
        'status': 'ok',
        'service': 'YouTube AI Assistant API',
        'systems': {
            'multi_agent': 'available',
            'simple_contextual': 'available',
            'transcript_processor': 'available'
        }
    })

@app.route('/debug/analyze', methods=['POST'])
def debug_analyze():
    """
    Endpoint de debug pour tester uniquement l'analyseur de questions
    """
    try:
        data = request.get_json()
        question = data.get("question", "")
        
        if not question:
            return jsonify({"error": "Question requise"}), 400
        
        # Données contextuelles de test
        test_context = {
            'current_time_formatted': '05:30',
            'priority_window_text': '[05:25] Exemple de contexte prioritaire...',
            'extended_context_summary': 'Exemple de contexte étendu...'
        }
        
        # Analyser seulement
        analysis = multi_agent_assistant.analyze_question(question, test_context)
        
        return jsonify({
            'question': question,
            'analysis': analysis
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Vérifier la clé API
    print("🚀 Démarrage du serveur backend avec système Multi-Agents...")
    print("📝 Endpoints disponibles:")
    print("   POST /ask - Poser une question (multi-agents)")
    print("   POST /ask/simple - Poser une question (système simple)")
    print("   GET /transcript/<video_id> - Info sur le transcript")
    print("   POST /debug/analyze - Debug de l'analyseur")
    print("   GET /health - Status du serveur")
    
    # Vérifier les dépendances
    try:
        from langchain.chat_models import ChatOpenAI
        print("✅ LangChain disponible")
    except ImportError:
        print("❌ LangChain non installé. Installez avec: pip install langchain openai")
    
    app.run(debug=True, port=5000, use_reloader=False)