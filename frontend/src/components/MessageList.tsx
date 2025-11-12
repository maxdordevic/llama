import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader, CheckCircle, XCircle, Clock, Zap, Brain, Code, Search } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: any;
  status?: 'sending' | 'success' | 'error';
}

interface Progress {
  stage: string;
  message: string;
  task?: any;
  progress?: any;
}

interface MessageListProps {
  messages: Message[];
}

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const getAgentIcon = (agentType?: string) => {
    switch (agentType) {
      case 'research': return <Search className="w-4 h-4" />;
      case 'code': return <Code className="w-4 h-4" />;
      case 'data': return <Brain className="w-4 h-4" />;
      default: return <Zap className="w-4 h-4" />;
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
        >
          <div
            className={`max-w-3xl rounded-2xl p-4 shadow-lg ${
              message.role === 'user'
                ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700'
            }`}
          >
            {/* Message Header */}
            <div className="flex items-center gap-2 mb-2">
              {message.role === 'assistant' && (
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                    <Zap className="w-4 h-4 text-white" />
                  </div>
                  <span className="font-semibold text-gray-900 dark:text-white">
                    Manus AI
                  </span>
                </div>
              )}
              {message.role === 'user' && (
                <span className="font-semibold">You</span>
              )}
              <span className="text-xs opacity-70 ml-auto">
                {new Date(message.timestamp).toLocaleTimeString()}
              </span>
            </div>

            {/* Message Content */}
            <div className={`prose ${message.role === 'user' ? 'prose-invert' : 'dark:prose-invert'} max-w-none`}>
              <ReactMarkdown
                components={{
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        className="rounded-lg"
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>

            {/* Message Status */}
            {message.status && (
              <div className="flex items-center gap-2 mt-2 text-xs">
                {message.status === 'sending' && (
                  <>
                    <Loader className="w-3 h-3 animate-spin" />
                    <span>Sending...</span>
                  </>
                )}
                {message.status === 'success' && (
                  <>
                    <CheckCircle className="w-3 h-3 text-green-500" />
                    <span>Delivered</span>
                  </>
                )}
                {message.status === 'error' && (
                  <>
                    <XCircle className="w-3 h-3 text-red-500" />
                    <span>Failed</span>
                  </>
                )}
              </div>
            )}

            {/* Metadata (execution time, etc.) */}
            {message.metadata && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                <div className="flex flex-wrap gap-3 text-xs">
                  {message.metadata.execution_time && (
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      <span>{message.metadata.execution_time.toFixed(1)}s</span>
                    </div>
                  )}
                  {message.metadata.plan && (
                    <div className="flex items-center gap-1">
                      <Brain className="w-3 h-3" />
                      <span>{message.metadata.plan.subtasks?.length || 0} tasks</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;
