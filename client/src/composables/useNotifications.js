import { ref, onMounted, onUnmounted } from 'vue';
import api from '@/services/api';
import { useToast } from './useToast';

const notifications = ref([]);
const unreadCount = ref(0);
const isOpen = ref(false);
let ws = null;
let reconnectTimer = null;

const { add: toast } = useToast();

const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/notifications`;

function connect() {
  const token = localStorage.getItem('access_token');
  if (!token) return;

  try {
    ws = new WebSocket(`${WS_URL}?token=${token}`);

    ws.onopen = () => {
      console.log('[WS] Connected');
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'notification') {
          notifications.value.unshift(payload.data);
          unreadCount.value += 1;
          toast(payload.data.title, 'info');
        }
      } catch {
        // ignore
      }
    };

    ws.onclose = () => {
      ws = null;
      reconnectTimer = setTimeout(connect, 5000);
    };

    ws.onerror = () => {
      ws?.close();
    };
  } catch {
    // ignore
  }
}

function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  ws?.close();
  ws = null;
}

async function fetchNotifications() {
  try {
    const { data } = await api.get('/notifications/');
    notifications.value = data.items || [];
    unreadCount.value = data.unread_count || 0;
  } catch {
    // ignore
  }
}

async function markAsRead(id) {
  try {
    await api.patch(`/notifications/${id}/read`);
    const n = notifications.value.find((item) => item.id === id);
    if (n && !n.is_read) {
      n.is_read = true;
      unreadCount.value = Math.max(0, unreadCount.value - 1);
    }
  } catch {
    // ignore
  }
}

async function markAllAsRead() {
  try {
    await api.patch('/notifications/read-all');
    notifications.value.forEach((n) => { n.is_read = true; });
    unreadCount.value = 0;
  } catch {
    // ignore
  }
}

async function deleteNotification(id) {
  try {
    await api.delete(`/notifications/${id}`);
    const idx = notifications.value.findIndex((n) => n.id === id);
    if (idx !== -1) {
      const wasUnread = !notifications.value[idx].is_read;
      notifications.value.splice(idx, 1);
      if (wasUnread) unreadCount.value = Math.max(0, unreadCount.value - 1);
    }
  } catch {
    // ignore
  }
}

export function useNotifications() {
  onMounted(() => {
    fetchNotifications();
    connect();
  });

  onUnmounted(() => {
    disconnect();
  });

  return {
    notifications,
    unreadCount,
    isOpen,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    deleteNotification,
  };
}
