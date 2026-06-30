<template>
  <div class="verify-email-page" data-testid="verify-email-page">
    <div class="verify-email-card">
      <div v-if="loading" class="verify-email-loading" data-testid="verify-email-loading">
        <div class="spinner"></div>
        <p>Подтверждаем email...</p>
      </div>

      <div v-else-if="error" class="verify-email-error" data-testid="verify-email-error">
        <p>{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { verifyEmail } from '@/api/auth';

const route = useRoute();
const router = useRouter();

const loading = ref(true);
const error = ref('');
const isMounted = ref(true);

onUnmounted(() => {
  isMounted.value = false;
});

function parseRedirectPath(responseURL) {
  if (!responseURL) return null;
  try {
    const url = new URL(responseURL, window.location.origin);
    return url.pathname + url.search;
  } catch {
    return null;
  }
}

onMounted(async () => {
  const token = route.query.token;
  if (!token || typeof token !== 'string') {
    router.replace('/verify-email/error?reason=invalid');
    if (isMounted.value) {
      loading.value = false;
    }
    return;
  }

  try {
    const response = await verifyEmail(token);
    // Браузер прозрачно следует 302-редиректам, поэтому проверяем
    // фактический URL ответа и направляем пользователя на success/error.
    const finalPath = parseRedirectPath(response.request?.responseURL);
    if (finalPath && finalPath.startsWith('/verify-email/error')) {
      router.replace(finalPath);
    } else if (finalPath && finalPath.startsWith('/verify-email/success')) {
      router.replace(finalPath);
    } else {
      router.replace('/verify-email/success');
    }
  } catch (err) {
    if (err.response?.status === 302) {
      const location = err.response.headers?.location;
      if (location) {
        const url = new URL(location, window.location.origin);
        router.replace(url.pathname + url.search);
        return;
      }
    }

    const reason = err.response?.data?.reason || 'invalid';
    router.replace(`/verify-email/error?reason=${reason}`);
  } finally {
    if (isMounted.value) {
      loading.value = false;
    }
  }
});
</script>

<style scoped>
.verify-email-page {
  background: var(--color-bg);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
}

.verify-email-card {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 32px 24px;
  max-width: 420px;
  width: 100%;
  text-align: center;
}

.verify-email-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: var(--color-text);
  font-size: 16px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.verify-email-error {
  color: var(--color-danger);
  font-size: 14px;
}
</style>
