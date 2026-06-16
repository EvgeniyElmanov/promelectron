import { ref, computed } from 'vue';
import api from '@/services/api';

const ALL_LIMIT = 1000;
const PAGE_LIMIT = 20;

export function useCategories() {
  const allCategories = ref([]);
  const displayedCategories = ref([]);
  const activeTab = ref(null); // null = "Все"
  const searchQuery = ref('');
  const loading = ref(false);
  const total = ref(0);
  const skip = ref(0);

  const rootCategories = computed(() =>
    allCategories.value
      .filter((category) => category.parent_id === null)
      .sort((a, b) => a.id - b.id)
  );

  const buildListParams = () => {
    const isAllTab = activeTab.value === null;
    const params = {
      skip: isAllTab ? skip.value : 0,
      limit: isAllTab ? PAGE_LIMIT : ALL_LIMIT,
    };
    const q = searchQuery.value.trim();
    if (q) {
      params.q = q;
    }
    if (!isAllTab) {
      params.parent_id = activeTab.value;
    }
    return params;
  };

  const fetchAllCategories = async () => {
    try {
      const { data } = await api.get('/categories/', {
        params: { skip: 0, limit: ALL_LIMIT },
      });
      allCategories.value = data.items || [];
    } catch {
      allCategories.value = [];
    }
  };

  const fetchDisplayedCategories = async () => {
    loading.value = true;
    try {
      const { data } = await api.get('/categories/', {
        params: buildListParams(),
      });
      displayedCategories.value = data.items || [];
      total.value = data.total || 0;
    } finally {
      loading.value = false;
    }
  };

  const setActiveTab = async (tabId) => {
    activeTab.value = tabId;
    skip.value = 0;
    await fetchDisplayedCategories();
  };

  const setSearchQuery = async (q) => {
    searchQuery.value = q;
    skip.value = 0;
    await fetchDisplayedCategories();
  };

  const loadMore = async () => {
    if (activeTab.value !== null) return;
    skip.value += PAGE_LIMIT;
    try {
      const { data } = await api.get('/categories/', {
        params: buildListParams(),
      });
      displayedCategories.value.push(...(data.items || []));
      total.value = data.total || 0;
    } catch {
      skip.value -= PAGE_LIMIT;
    }
  };

  return {
    allCategories,
    displayedCategories,
    rootCategories,
    activeTab,
    searchQuery,
    loading,
    total,
    skip,
    fetchAllCategories,
    fetchDisplayedCategories,
    setActiveTab,
    setSearchQuery,
    loadMore,
  };
}
