import React from 'react';
import { Activity, Cpu, Zap, Clock } from 'lucide-react';

const AgentMonitor: React.FC = () => {
  const agents = [
    { name: 'Research Agent', type: 'research', status: 'idle', tasks: 0 },
    { name: 'Code Agent', type: 'code', status: 'idle', tasks: 0 },
    { name: 'Web Agent', type: 'web', status: 'idle', tasks: 0 },
    { name: 'Data Agent', type: 'data', status: 'idle', tasks: 0 },
    { name: 'File Agent', type: 'file', status: 'idle', tasks: 0 },
    { name: 'General Agent', type: 'general', status: 'idle', tasks: 0 },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Agent Monitor
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Real-time status of all AI agents
        </p>
      </div>

      {/* System Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Activity className="w-6 h-6 text-blue-500" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Active Tasks</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">0</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <Cpu className="w-6 h-6 text-green-500" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Agents Ready</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">6</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Zap className="w-6 h-6 text-purple-500" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Completed</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">0</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
              <Clock className="w-6 h-6 text-orange-500" />
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Avg Time</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">-</p>
            </div>
          </div>
        </div>
      </div>

      {/* Agent List */}
      <div className="grid gap-4">
        {agents.map((agent) => (
          <div
            key={agent.type}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold">
                  {agent.name.substring(0, 1)}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    {agent.name}
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Type: {agent.type}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Tasks</p>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">
                    {agent.tasks}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-sm text-green-600 dark:text-green-400 capitalize">
                    {agent.status}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AgentMonitor;
