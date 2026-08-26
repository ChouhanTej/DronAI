/**
 * Real-Time Telemetry WebSocket Service
 * Connects to FastAPI backend WebSocket server with auto-reconnect.
 */

class TelemetryWebSocket {
  constructor(url = 'ws://localhost:8000/ws/telemetry') {
    this.url = url;
    this.ws = null;
    this.onMessageCallback = null;
    this.onStatusChangeCallback = null;
    this.isConnecting = false;
    this.reconnectInterval = 2000;
  }

  connect(onMessage, onStatusChange) {
    this.onMessageCallback = onMessage;
    this.onStatusChangeCallback = onStatusChange;

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isConnecting = true;
    if (this.onStatusChangeCallback) this.onStatusChangeCallback(false, 'Connecting...');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.isConnecting = false;
        if (this.onStatusChangeCallback) this.onStatusChangeCallback(true, 'Connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (this.onMessageCallback) {
            this.onMessageCallback(data);
          }
        } catch (e) {
          console.error('[WS PARSE ERROR]', e);
        }
      };

      this.ws.onclose = () => {
        this.isConnecting = false;
        if (this.onStatusChangeCallback) this.onStatusChangeCallback(false, 'Disconnected');
        setTimeout(() => this.connect(this.onMessageCallback, this.onStatusChangeCallback), this.reconnectInterval);
      };

      this.ws.onerror = (err) => {
        this.isConnecting = false;
        if (this.onStatusChangeCallback) this.onStatusChangeCallback(false, 'Connection Error');
      };
    } catch (err) {
      this.isConnecting = false;
      if (this.onStatusChangeCallback) this.onStatusChangeCallback(false, 'Offline');
      setTimeout(() => this.connect(this.onMessageCallback, this.onStatusChangeCallback), this.reconnectInterval);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const wsService = new TelemetryWebSocket();
