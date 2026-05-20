<template>
  <div class="notifications-page" data-testid="notifications-page">
    <div class="notifications-page__header">
      <button class="notifications-page__back" @click="router.back()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
      </button>
      <h1 class="notifications-page__title">Уведомления</h1>
      <button
        v-if="unreadCount > 0"
        class="notifications-page__read-all"
        @click="markAllAsRead"
      >
        Прочитать все
      </button>
    </div>

    <div v-if="loading" class="notifications-page__loading">Загрузка...</div>

    <div v-else-if="notifications.length === 0" class="notifications-page__empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 01-3.46 0"/>
      </svg>
      <p>У вас пока нет уведомлений</p>
    </div>

    <div v-else class="notifications-page__list">
      <div
        v-for="n in notifications"
        :key="n.id"
        class="notification-item"
        :class="{ 'notification-item--unread': !n.is_read }"
        @click="onClick(n)"
      >
        <div class="notification-item__dot" v-if="!n.is_read"></div>
        <div class="notification-item__content">
          <div class="notification-item__title">{{ n.title }}</div>
          <div class="notification-item__message">{{ n.message }}</div>
          <div class="notification-item__time">{{ formatTime(n.created_at) }}</div>
        </div>
        <button class="notification-item__delete" @click.stop="remove(n.id)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';

const router = useRouter();
const notifications = ref([]);
const unreadCount = ref(0);
const loading = ref(true);

const fetchNotifications = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/notifications/');
    notifications.value = data.items || [];
    unreadCount.value = data.unread_count || 0;
  } catch {
    // ignore
  } finally {
    loading.value = false;
  }
};

const markAllAsRead = async () => {
  try {
    await api.patch('/notifications/read-all');
    notifications.value.forEach((n) => { n.is_read = true; });
    unreadCount.value = 0;
  } catch {
    // ignore
  }
};

const onClick = async (n) => {
  if (!n.is_read) {
    try {
      await api.patch(`/notifications/${n.id}/read`);
      n.is_read = true;
      unreadCount.value = Math.max(0, unreadCount.value - 1);
    } catch {
      // ignore
    }
  }
  if (n.order_id) {
    router.push(`/orders/${n.order_id}`);
  }
};

const remove = async (id) => {
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
};

function formatTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' });
}

onMounted(fetchNotifications);
</script>

<style scoped>
.notifications-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 16px;
  min-height: 100vh;
  background: var(--color-bg);
}

.notifications-page__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.notifications-page__back {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: var(--color-bg-white);
  color: var(--color-text);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.notifications-page__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
  flex: 1;
}

.notifications-page__read-all {
  padding: 8px 14px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  border: none;
  cursor: pointer;
}

.notifications-page__loading,
.notifications-page__empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-secondary);
}

.notifications-page__empty svg {
  margin-bottom: 12px;
  color: var(--color-text-secondary);
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: var(--color-bg-white);
  border-radius: 14px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.notification-item:hover {
  background: var(--color-bg);
}

.notification-item--unread {
  background: #f0f7ff;
}

.notification-item--unread:hover {
  background: #e0efff;
}

.notification-item__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  margin-top: 6px;
  flex-shrink: 0;
}

.notification-item__content {
  flex: 1;
  min-width: 0;
}

.notification-item__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 2px;
}

.notification-item__message {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.notification-item__time {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.notification-item__delete {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

.notification-item__delete:hover {
  background: #fff0f0;
  color: var(--color-danger);
}
</style>
