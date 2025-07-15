import { defineStore } from 'pinia';
import { ref } from 'vue';
import { useCacheStore } from './cache';

export const useDataStore = defineStore('data', () => {
    const isDataUploaded = ref(false);
    const fileName = ref('');
    const cacheFileName = ref('');
    const description = ref(``);
    const fields = ref([]);
    const selectedDatasetId = ref('');

    function uploadData(formData, cb) {
        const cacheStore = useCacheStore();

        fetch(`http://localhost:5000/summarize_data?cache_path=case1_cache&use_cache=${cacheStore.isUseCache}&update_cache=${cacheStore.isUpdateCache}`, {
            method: 'POST',
            body: formData,
        })
            .then(response => response.json())
            .then(data => {
                fileName.value = data.name;
                fields.value = data.fields;
                description.value = data.dataset_description;
                isDataUploaded.value = true;
                if (cb)
                    cb();
            })
            .catch(err => {
                alert('Failed to upload data');
                console.error(err);
                if (cb)
                    cb();
            })
    }

    return {
        isDataUploaded,
        fileName,
        cacheFileName,
        description,
        fields,
        selectedDatasetId,
        uploadData,
    };
});