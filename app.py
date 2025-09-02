# app.py - Backend Flask avec système de mémoire
from flask import Flask, request, jsonify
from flask_cors import CORS
from memory_system import ContextualTranscriptProcessorWithMemory
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)  # Permettre les requêtes depuis l'extension

# Initialiser le processeur avec mémoire
API_KEY = os.getenv('OPENAI_API_KEY', 'api_key')
processor = ContextualTranscriptProcessorWithMemory(API_KEY)

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
        user_id = data.get("user_id", "browser_session")  # ID utilisateur pour la session

        print("✅ Paramètres extraits:")
        print(f"   - video_id: '{video_id}' (type: {type(video_id)})")
        print(f"   - current_time: {current_time} (type: {type(current_time)})")
        print(f"   - question: '{question}' (type: {type(question)})")
        print(f"   - user_id: '{user_id}'")

        # Validation
        if not video_id or not question:
            print(f"❌ Validation échouée: video_id='{video_id}', question='{question}'")
            return jsonify({
                "error": "video_id et question sont requis",
                "received_video_id": video_id,
                "received_question": question
            }), 400

        # Traitement avec mémoire
        result = processor.ask_question_with_memory(video_id, current_time, question, user_id)

        # Vérifier s'il y a une erreur
        if "error" in result:
            return jsonify({
                "error": result["error"],
                "video_id": video_id
            }), 500

        # Log de l'analyse
        print("✅ Question traitée avec mémoire:")
        print(f"   - Historique présent: {result.get('has_conversation_history', False)}")
        print(f"   - Longueur conversation: {result.get('conversation_length', 0)}")

        # Stats mémoire
        memory_stats = processor.get_conversation_stats()
        print(f"📊 Stats mémoire: {memory_stats}")

        return jsonify({
            "response": result.get("response", ""),
            "video_id": video_id,
            "timestamp": current_time,
            "memory": {
                "has_history": result.get("has_conversation_history", False),
                "conversation_length": result.get("conversation_length", 0),
                "session_stats": memory_stats
            },
            "debug_info": f"Mémoire: {result.get('conversation_length', 0)} messages en historique"
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
    Endpoint alternatif SANS mémoire (pour comparaison)
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

        # Utiliser la méthode sans mémoire du processeur
        result = processor.transcript_processor.ask_question(video_id, current_time, question)

        return jsonify({
            "response": result,
            "video_id": video_id,
            "timestamp": current_time,
            "system": "simple_sans_memoire"
        })

    except Exception as e:
        print(f"🚨 Erreur simple: {e}")
        return jsonify({
            "error": "Erreur interne du serveur",
            "details": str(e)
        }), 500


@app.route('/conversation/clear/<video_id>', methods=['POST'])
def clear_conversation(video_id):
    """Efface l'historique de conversation pour une vidéo"""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id", "browser_session")
        
        processor.clear_conversation(video_id, user_id)
        
        return jsonify({
            "success": True,
            "message": f"Conversation effacée pour la vidéo {video_id}",
            "video_id": video_id
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route('/conversation/history/<video_id>', methods=['GET'])
def get_conversation_history(video_id):
    """Récupère l'historique de conversation pour une vidéo"""
    try:
        user_id = request.args.get('user_id', 'browser_session')
        history = processor.memory.get_conversation_history(video_id, user_id)
        
        return jsonify({
            "video_id": video_id,
            "user_id": user_id,
            "history": history,
            "message_count": len(history)
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route('/memory/stats', methods=['GET'])
def get_memory_stats():
    """Statistiques du système de mémoire"""
    try:
        stats = processor.get_conversation_stats()
        
        # Nettoyer les sessions expirées
        cleaned_count = processor.memory.cleanup_expired_sessions()
        
        return jsonify({
            "stats": stats,
            "cleaned_expired_sessions": cleaned_count,
            "status": "ok"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route('/transcript/<video_id>', methods=['GET'])
def get_transcript_info(video_id):
    """Endpoint pour récupérer des infos sur le transcript"""
    try:
        transcript = processor.transcript_processor.get_transcript(video_id)
        
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
    try:
        memory_stats = processor.get_conversation_stats()
        
        return jsonify({
            'status': 'ok',
            'service': 'YouTube AI Assistant API avec Mémoire',
            'memory': memory_stats,
            'features': {
                'conversation_memory': 'enabled',
                'session_timeout': '30 minutes',
                'max_messages_per_session': 10
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Vérifier la clé API
    print("🚀 Démarrage du serveur backend avec système de MÉMOIRE...")
    print("📝 Endpoints disponibles:")
    print("   POST /ask - Poser une question (AVEC mémoire)")
    print("   POST /ask/simple - Poser une question (SANS mémoire)")
    print("   POST /conversation/clear/<video_id> - Effacer l'historique")
    print("   GET /conversation/history/<video_id> - Voir l'historique")
    print("   GET /memory/stats - Statistiques mémoire")
    print("   GET /transcript/<video_id> - Info sur le transcript")
    print("   GET /health - Status du serveur")
    print()
    print("🧠 Fonctionnalités mémoire:")
    print("   ✅ Se souvient des conversations précédentes par vidéo")
    print("   ✅ Timeout de session: 30 minutes")
    print("   ✅ Maximum 10 messages par session")
    print("   ✅ Nettoyage automatique des sessions expirées")
    
    app.run(debug=True, port=5000, use_reloader=False)