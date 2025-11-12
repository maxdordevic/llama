import React from 'react';
import { CheckCircle, Circle, Loader, XCircle, Clock } from 'lucide-react';

interface ProgressTrackerProps {
  progress: any;
}

const ProgressTracker: React.FC<ProgressTrackerProps> = ({ progress }) => {
  if (!progress) return null;

  const getStageIcon = (stage: string) => {
    switch (stage) {
      case 'complete':
      case 'completed':
      case 'task_completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'in_progress':
      case 'task_started':
      case 'execution':
        return <Loader className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'error':
      case 'task_failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Circle className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStageColor = (stage: string) => {
    switch (stage) {
      case 'complete':
      case 'completed':
      case 'task_completed':
        return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
      case 'in_progress':
      case 'task_started':
      case 'execution':
        return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
      case 'error':
      case 'task_failed':
        return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
      case 'planning':
        return 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800';
      default:
        return 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700';
    }
  };

  return (
    <div className="mx-6 mb-4 animate-slideUp">
      <div className={`rounded-xl border-2 ${getStageColor(progress.stage)} p-4 shadow-lg backdrop-blur-sm`}>
        {/* Header */}
        <div className="flex items-center gap-3 mb-3">
          <div className="flex-shrink-0">
            {getStageIcon(progress.stage)}
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 dark:text-white capitalize">
              {progress.stage.replace(/_/g, ' ')}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {progress.message}
            </p>
          </div>
        </div>

        {/* Task Details */}
        {progress.task && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-start gap-2">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-xs font-bold">
                {progress.task.agent_type?.substring(0, 1).toUpperCase() || 'A'}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {progress.task.title}
                </p>
                {progress.task.description && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    {progress.task.description}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Overall Progress */}
        {progress.progress && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-gray-600 dark:text-gray-400">Overall Progress</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {progress.progress.completed}/{progress.progress.total} tasks
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progress.progress.progress || 0}%` }}
              />
            </div>
            <div className="flex items-center gap-4 mt-2 text-xs text-gray-600 dark:text-gray-400">
              <div className="flex items-center gap-1">
                <CheckCircle className="w-3 h-3 text-green-500" />
                <span>{progress.progress.completed} completed</span>
              </div>
              {progress.progress.in_progress > 0 && (
                <div className="flex items-center gap-1">
                  <Loader className="w-3 h-3 text-blue-500 animate-spin" />
                  <span>{progress.progress.in_progress} in progress</span>
                </div>
              )}
              {progress.progress.failed > 0 && (
                <div className="flex items-center gap-1">
                  <XCircle className="w-3 h-3 text-red-500" />
                  <span>{progress.progress.failed} failed</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Timestamp */}
        {progress.timestamp && (
          <div className="flex items-center gap-1 mt-3 text-xs text-gray-500 dark:text-gray-500">
            <Clock className="w-3 h-3" />
            <span>{new Date(progress.timestamp).toLocaleTimeString()}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProgressTracker;
