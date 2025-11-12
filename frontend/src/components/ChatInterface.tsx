import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader } from 'lucide-react';
import { sendMessage, createSession } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import MessageList from './MessageList';
import ProgressTracker from './ProgressTracker';

interface ChatInterfaceProps {
  userId: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ userId }) => {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [progress, setProgress] = useState<any>(null);

  const inputRef = useRef<HTMLTextAreaElement>(null);

  // WebSocket connection for real-time updates
  const { isConnected, sendMessage: wsSend } = useWebSocket(
    sessionId ? `ws://localhost:8000/ws/${sessionId}` : null,
    (data) => {
      // Handle progress updates
      if (data.stage === 'task_started' || data.stage === 'task_completed') {
        setProgress(data);
      }
    }
  );

  useEffect(() => {
    // Initialize session
    const initSession = async () => {
      try {
        const response = await createSession({ user_id: userId });
        setSessionId(response.data.id);
      } catch (error) {
        console.error('Failed to create session:', error);
      }
    };

    initSession();
  }, [userId]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendMessage({
        message: input,
        user_id: userId,
        session_id: sessionId || undefined
      });

      if (!sessionId) {
        setSessionId(response.data.session_id);
      }

      const assistantMessage = {
        role: 'assistant',
        content: response.data.message,
        timestamp: new Date().toISOString(),
        metadata: response.data.metadata
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);

      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request.',
        timestamp: new Date().toISOString(),
        error: true
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      setProgress(null);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-container">
        <MessageList messages={messages} />

        {progress && (
          <ProgressTracker progress={progress} />
        )}

        <div className="chat-input-container">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Describe your task... (e.g., 'Research the latest AI trends and create a presentation')"
            disabled={loading}
            rows={3}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="send-button"
          >
            {loading ? <Loader className="spinning" /> : <Send />}
          </button>
        </div>

        <div className="chat-info">
          <span className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '● Connected' : '○ Disconnected'}
          </span>
          {sessionId && <span className="session-id">Session: {sessionId.slice(0, 8)}...</span>}
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
