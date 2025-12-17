import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default function ErrorState({ error, onRetry }) {
  // Parse error message
  const errorMessage = error?.response?.data?.detail
    || error?.response?.data?.message
    || error?.message
    || 'An unexpected error occurred';

  return (
    <div className="w-full max-w-md mx-auto text-center py-12">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-900/50 mb-4">
        <AlertCircle className="h-8 w-8 text-red-400" />
      </div>

      <h2 className="text-xl font-bold text-white mb-2">Analysis Failed</h2>

      <p className="text-gray-400 mb-6">{errorMessage}</p>

      <div className="space-y-3">
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700
                     text-white font-medium rounded-lg transition-colors"
        >
          <RefreshCw className="h-5 w-5" />
          Try Again
        </button>

        <p className="text-sm text-gray-500">
          Make sure the backend server is running at{' '}
          <code className="bg-gray-800 px-1 rounded">localhost:8001</code>
        </p>
      </div>
    </div>
  );
}
