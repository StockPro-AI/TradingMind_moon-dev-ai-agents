import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5 minutes - analysis can take a while
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Get API health status and current configuration
 */
export const getHealth = async () => {
  const response = await axios.get('/');
  return response.data;
};

/**
 * Get current configuration
 */
export const getConfig = async () => {
  const response = await api.get('/config');
  return response.data;
};

/**
 * Update configuration
 */
export const updateConfig = async (config) => {
  const response = await api.post('/config', config);
  return response.data;
};

/**
 * Run stock analysis
 * @param {string} ticker - Stock ticker symbol (e.g., "AAPL")
 * @param {string} date - Analysis date in YYYY-MM-DD format
 * @param {object} config - Optional custom configuration
 * @returns {Promise<object>} Analysis result with categorized content
 */
export const analyzeStock = async (ticker, date, config = null) => {
  const response = await api.post('/analyze', {
    ticker: ticker.toUpperCase(),
    date,
    config,
    compare_providers: false,
  });
  return response.data;
};

/**
 * Get analysis history for a ticker
 * @param {string} ticker - Stock ticker symbol
 */
export const getAnalysisHistory = async (ticker) => {
  const response = await api.get(`/history/${ticker.toUpperCase()}`);
  return response.data;
};

/**
 * Get available LLM models
 */
export const getModels = async () => {
  const response = await api.get('/models');
  return response.data;
};

/**
 * WebSocket connection for real-time analysis updates
 */
export class AnalysisWebSocket {
  constructor(onMessage, onError, onClose) {
    this.ws = null;
    this.onMessage = onMessage;
    this.onError = onError;
    this.onClose = onClose;
  }

  connect(ticker, date) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;

    // Use the proxy configured in vite.config.js
    this.ws = new WebSocket(`${protocol}//${host}/ws/analyze`);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      // Send analysis request
      this.ws.send(JSON.stringify({
        ticker: ticker.toUpperCase(),
        date,
      }));
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.onMessage(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (this.onError) this.onError(error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed');
      if (this.onClose) this.onClose();
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export default api;
