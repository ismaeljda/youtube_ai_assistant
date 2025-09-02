class YouTubeAIAssistant {
  constructor() {
    console.log('📱 Initialisation de YouTubeAIAssistant');
    this.isInitialized = false;
    this.chatContainer = null;
    this.isVisible = false;
    this.currentVideoId = null;
    this.init();
  }

  init() {
    console.log('🔄 Init() appelé, document.readyState:', document.readyState);
    // Attendre que la page YouTube soit chargée
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setup());
    } else {
      this.setup();
    }
  }

  setup() {
    console.log('⚙️ Setup() appelé');
    // Détecter les changements de vidéo YouTube (SPA)
    this.observeVideoChanges();
    this.createAIButton();
    this.createChatInterface();
    console.log('✅ Setup terminé');
  }

  observeVideoChanges() {
    // Observer les changements d'URL pour détecter les nouvelles vidéos
    let lastUrl = location.href;
    new MutationObserver(() => {
      const url = location.href;
      if (url !== lastUrl) {
        lastUrl = url;
        if (url.includes('/watch')) {
          this.onVideoChanged();
        }
      }
    }).observe(document, { subtree: true, childList: true });
  }

  onVideoChanged() {
    const videoId = this.extractVideoId();
    if (videoId !== this.currentVideoId) {
      this.currentVideoId = videoId;
      console.log('Nouvelle vidéo détectée:', videoId);
      // Reset du chat pour la nouvelle vidéo
      this.clearChat();
    }
  }

  extractVideoId() {
    const urlParams = new URLSearchParams(window.location.search);
    const videoId = urlParams.get('v');
    console.log('🎬 Video ID extraite:', videoId, 'depuis URL:', window.location.href);
    return videoId;
  }

  createAIButton() {
    console.log('🔘 Création du bouton AI...');
    
    // Version simplifiée avec délai
    const tryInsertButton = () => {
      // Sélecteurs plus fiables selon ChatGPT
      const container = document.querySelector('#top-row') || 
                       document.querySelector('.ytd-watch-metadata') ||
                       document.querySelector('#container #primary') ||
                       document.querySelector('ytd-watch-metadata') ||
                       document.body; // Fallback sur body
      
      console.log('🔍 Container trouvé:', container);
      
      if (container && !document.querySelector('#ai-assistant-btn')) {
        console.log('✅ Insertion du bouton AI');
        // Délai de 2 secondes comme suggéré
        setTimeout(() => {
          this.insertAIButton(container);
        }, 2000);
        return true;
      }
      return false;
    };
    
    // Essayer immédiatement
    if (tryInsertButton()) return;
    
    // Sinon observer
    const observer = new MutationObserver(() => {
      if (tryInsertButton()) {
        observer.disconnect();
      }
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
    
    // Timeout de sécurité
    setTimeout(() => {
      observer.disconnect();
      console.log('⏰ Timeout atteint');
    }, 10000);
  }

  insertAIButton(container) {
    console.log('➕ Insertion du bouton dans:', container);
    
    // TOUJOURS utiliser la position fixe pour éviter les problèmes
    console.log('🎯 Utilisation position fixed pour garantir la visibilité');
    const aiButton = document.createElement('div');
    aiButton.id = 'ai-assistant-btn';
    aiButton.style.cssText = `
      position: fixed !important;
      top: 120px !important;
      right: 20px !important;
      background: #1976d2 !important;
      color: white !important;
      padding: 12px 16px !important;
      border-radius: 8px !important;
      cursor: pointer !important;
      z-index: 10000 !important;
      font-family: Roboto, Arial, sans-serif !important;
      font-size: 14px !important;
      font-weight: 500 !important;
      box-shadow: 0 4px 12px rgba(25, 118, 210, 0.3) !important;
      display: flex !important;
      align-items: center !important;
      gap: 8px !important;
      transition: all 0.2s ease !important;
      border: none !important;
    `;
    aiButton.innerHTML = `🤖 Ask AI`;
    
    aiButton.addEventListener('click', () => {
      console.log('🎯 Bouton AI cliqué !');
      this.toggleChat();
    });
    
    // Effets hover
    aiButton.addEventListener('mouseenter', () => {
      aiButton.style.background = '#1565c0 !important';
      aiButton.style.transform = 'translateY(-2px) scale(1.05) !important';
    });
    
    aiButton.addEventListener('mouseleave', () => {
      aiButton.style.background = '#1976d2 !important';
      aiButton.style.transform = 'translateY(0) scale(1) !important';
    });
    
    document.body.appendChild(aiButton);
    console.log('✅ Bouton AI ajouté en position fixe avec succès !');
  }

  createChatInterface() {
    // Créer le conteneur du chat
    this.chatContainer = document.createElement('div');
    this.chatContainer.id = 'ai-chat-container';
    this.chatContainer.className = 'ai-chat-container hidden';
    
    this.chatContainer.innerHTML = `
      <div class="ai-chat-header">
        <h3>AI Assistant</h3>
        <button class="ai-chat-close">&times;</button>
      </div>
      
      <div class="ai-chat-messages" id="ai-chat-messages">
        <div class="ai-message">
          <div class="message-content">
            👋 Salut ! Je peux t'aider à comprendre cette vidéo. Pose-moi une question sur ce que tu regardes !
          </div>
        </div>
      </div>
      
      <div class="ai-chat-input">
        <input type="text" id="ai-question-input" placeholder="Pose ta question..." />
        <button id="ai-send-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M2,21L23,12L2,3V10L17,12L2,14V21Z" />
          </svg>
        </button>
      </div>
      
      <div class="ai-chat-status" id="ai-chat-status"></div>
    `;

    // Ajouter les event listeners
    this.setupChatEvents();
    
    // Ajouter au DOM
    document.body.appendChild(this.chatContainer);
  }

  setupChatEvents() {
    // Fermer le chat
    this.chatContainer.querySelector('.ai-chat-close').addEventListener('click', () => {
      this.toggleChat();
    });

    // Envoyer une question
    const sendButton = this.chatContainer.querySelector('#ai-send-btn');
    const input = this.chatContainer.querySelector('#ai-question-input');
    
    sendButton.addEventListener('click', () => this.sendQuestion());
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.sendQuestion();
    });
  }

  toggleChat() {
    this.isVisible = !this.isVisible;
    this.chatContainer.classList.toggle('hidden', !this.isVisible);
    
    if (this.isVisible) {
      this.chatContainer.querySelector('#ai-question-input').focus();
    }
  }

  getCurrentTime() {
    // Récupérer le temps actuel de la vidéo YouTube
    const video = document.querySelector('video');
    return video ? video.currentTime : 0;
  }

  async sendQuestion() {
    const input = this.chatContainer.querySelector('#ai-question-input');
    const question = input.value.trim();
    
    if (!question) return;
    
    // Forcer la récupération de video_id au moment du clic
    const currentTime = this.getCurrentTime();
    const videoId = this.extractVideoId(); // Récupérer à nouveau au moment du clic
    
    console.log('🐛 Debug sendQuestion:');
    console.log('   - URL actuelle:', window.location.href);
    console.log('   - Search params:', window.location.search);
    console.log('   - videoId extraite:', videoId);
    console.log('   - currentTime:', currentTime);
    console.log('   - question:', question);
    console.log('   - this.currentVideoId:', this.currentVideoId);
    
    // Vérification supplémentaire
    if (!videoId) {
      this.addMessage('ai', '❌ Impossible de détecter l\'ID de la vidéo. Êtes-vous bien sur une page de vidéo YouTube ?');
      return;
    }
    
    // Ajouter la question de l'utilisateur au chat
    this.addMessage('user', question);
    input.value = '';
    
    // Afficher le status de chargement
    this.setStatus('Analyse de la vidéo...');
    
    try {
      // Appeler votre backend
      const response = await this.callBackend(videoId, currentTime, question);
      
      // Ajouter la réponse de l'IA au chat
      this.addMessage('ai', response);
      this.setStatus('');
      
    } catch (error) {
      console.error('Erreur:', error);
      this.addMessage('ai', 'Désolé, une erreur est survenue. Réessayez plus tard.');
      this.setStatus('');
    }
  }

  async callBackend(videoId, currentTime, question) {
    // Appel à votre API backend
    const response = await fetch('http://localhost:5000/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        video_id: videoId,
        current_time: currentTime,
        question: question
      })
    });
    
    if (!response.ok) {
      throw new Error('Erreur réseau');
    }
    
    const data = await response.json();
    return data.response;
  }

  addMessage(sender, content) {
    const messagesContainer = this.chatContainer.querySelector('#ai-chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `${sender}-message`;
    
    const timestamp = new Date().toLocaleTimeString('fr-FR', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    
    messageDiv.innerHTML = `
      <div class="message-content">${content}</div>
      <div class="message-time">${timestamp}</div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  setStatus(message) {
    const statusDiv = this.chatContainer.querySelector('#ai-chat-status');
    statusDiv.textContent = message;
    statusDiv.style.display = message ? 'block' : 'none';
  }

  clearChat() {
    const messagesContainer = this.chatContainer.querySelector('#ai-chat-messages');
    messagesContainer.innerHTML = `
      <div class="ai-message">
        <div class="message-content">
          👋 Nouvelle vidéo détectée ! Pose-moi une question sur ce que tu regardes.
        </div>
      </div>
    `;
  }
}

// Initialiser l'assistant quand la page est prête
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new YouTubeAIAssistant();
  });
} else {
  new YouTubeAIAssistant();
}