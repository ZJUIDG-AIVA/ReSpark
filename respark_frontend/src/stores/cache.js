import { defineStore } from 'pinia';
import { useDataStore } from './data';
import { useReportStore } from './report';
import { ref } from 'vue';

export const useCacheStore = defineStore('cache', () => {
    const isUseCache = ref(true);
    const isUpdateCache = ref(true);
    const cacheList = ref([]);
    const selectedCacheName = ref('');

    function toggleUseCache() {
        isUseCache.value = !isUseCache.value;
    }

    function toggleUpdateCache() {
        isUpdateCache.value = !isUpdateCache.value;
    }

    function getCacheList() {
        fetch('http://localhost:5000/get_cache_list')
            .then(response => response.json())
            .then(data => {
                cacheList.value = data;
            })
            .catch(err => {
                alert('Failed to get cache list');
                console.error(err);
            });
    }

    function createCache(name, cb) {
        const dataStore = useDataStore();
        const reportStore = useReportStore();

        fetch(`http://localhost:5000/create_cache`, {
            method: 'POST',
            body: JSON.stringify({
                name: name,
                selected_dataset_id: dataStore.selectedDatasetId,
                selected_report_id: reportStore.selectedReportId
            }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(() => {
                if (cb)
                    cb();
            })
            .catch(err => {
                alert('Failed to create cache');
                console.error(err);
                if (cb)
                    cb();
            });
    }

    return {
        selectedCacheName,
        isUseCache,
        isUpdateCache,
        cacheList,
        toggleUseCache,
        toggleUpdateCache,
        getCacheList,
        createCache,
    };
});