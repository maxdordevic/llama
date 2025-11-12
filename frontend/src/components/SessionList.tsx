import React from 'react';
import { Users, Clock, MessageSquare, Trash2 } from 'lucide-react';

interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: any[];
  status: string;
}

interface SessionListProps {
  userId: string;
}

const SessionList: React.FC<SessionListProps> = ({ userId }) => {
  const [sessions, setSessions] = React.useState<Session[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    loadSessions();
  }, [userId]);

  const loadSessions = async () => {
    try {
      // TODO: Implement API call to load sessions
      // const response = await listUserSessions(userId);
      // setSessions(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      setLoading(false);
    }
  };

  const deleteSession = async (sessionId: string) => {
    try {
      // TODO: Implement API call to delete session
      // await deleteSession(sessionId);
      setSessions(sessions.filter(s => s.id !== sessionId));
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Your Sessions
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          View and manage your conversation history
        </p>
      </div>

      {sessions.length === 0 ? (
        <div className="text-center py-12">
          <MessageSquare className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            No sessions yet
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Start a conversation to create your first session
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                    {session.title}
                  </h3>
                  <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                    <div className="flex items-center gap-1">
                      <MessageSquare className="w-4 h-4" />
                      <span>{session.messages.length} messages</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      <span>{new Date(session.updated_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => deleteSession(session.id)}
                  className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                  title="Delete session"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SessionList;
