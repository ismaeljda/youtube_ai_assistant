# app.py - Backend Flask
from flask import Flask, request, jsonify
from flask_cors import CORS
from contextual_transcript_processor import ContextualTranscriptProcessor
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)  # Permettre les requêtes depuis l'extension

# Initialiser le processeur avec votre clé API
API_KEY = os.getenv('OPENAI_API_KEY', 'api_key')
# processor = MultiAgentYouTubeAssistant(API_KEY)
processor = ContextualTranscriptProcessor(API_KEY)

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

        # Traitement via le processeur contextuel
        result = processor.ask_question(video_id, current_time, question)

        # Log de l'analyse
        if isinstance(result, dict) and "analysis" in result:
            print("✅ Analyse terminée:")
            print(f"   - Type de question: {result['analysis'].get('question_type', 'unknown')}")
            print(f"   - Stratégie: {result['analysis'].get('context_strategy', 'unknown')}")
            print(f"   - Contexte utilisé: {result.get('context_used', 0)} segments")

            return jsonify({
                "response": result.get("response", ""),
                "video_id": video_id,
                "timestamp": current_time,
                "analysis": {
                    "question_type": result["analysis"].get("question_type", "unknown"),
                    "strategy": result["analysis"].get("context_strategy", "unknown"),
                    "style": result["analysis"].get("response_style", "unknown")
                },
                "debug_info": f"Multi-agent: {result['analysis'].get('question_type', 'unknown')} question"
            })
        else:
            # Cas plus simple si `result` est juste une réponse texte
            return jsonify({
                "response": result,
                "video_id": video_id,
                "timestamp": current_time
            })

    except Exception as e:
        print(f"🚨 Erreur: {e}")
        return jsonify({
            "error": "Erreur interne du serveur",
            "details": str(e)
        }), 500


@app.route('/transcript/<video_id>', methods=['GET'])
def get_transcript_info(video_id):
    """Endpoint pour récupérer des infos sur le transcript"""
    try:
        transcript = processor.get_transcript(video_id)
        
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
        'service': 'YouTube AI Assistant API'
    })

if __name__ == '__main__':
    # Vérifier la clé API
    print("🚀 Démarrage du serveur backend...")
    print("📝 Endpoints disponibles:")
    print("   POST /ask - Poser une question contextuelle")
    print("   GET /transcript/<video_id> - Info sur le transcript")
    print("   GET /health - Status du serveur")
    
    app.run(debug=True, port=5000, use_reloader=False)
