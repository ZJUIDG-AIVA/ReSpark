<script setup>
import { ref, computed } from 'vue';
import { useCacheStore } from '@/stores/cache';
import { useDataStore } from '@/stores/data';
import { useReportStore } from '@/stores/report';
import RsButton from '@/components/basic/RsButton.vue';
import RsDialog from '@/components/basic/RsDialog.vue';

const props = defineProps(['direction']);

const cacheStore = useCacheStore();
const dataStore = useDataStore();
const reportStore = useReportStore();

const showCacheDialog = ref(false);
const cacheName = ref('');

const direction = computed(() => props.direction === 'row' ? 'row' : 'column');
const gap = computed(() => props.direction === 'row' ? '30px' : '10px');

function handleNewCache () {
    cacheName.value = '';
    showCacheDialog.value = true;
}
</script>

<template>
    <rs-dialog title="New Cache" :visible="showCacheDialog" @close="showCacheDialog = false" @submit="cacheStore.createCache(cacheName, () => { showCacheDialog = false; cacheStore.getCacheList(); })">
        <div class="dialog">
            <div class="sub-title">Cache Name</div>
            <input v-model="cacheName" />
        </div>
    </rs-dialog>
    <div class="cache-panel">
        <div class="options">
            <label class="checkbox-item"><input type="checkbox" v-model="cacheStore.isUseCache" />Use Cache</label>
            <label class="checkbox-item"><input type="checkbox" v-model="cacheStore.isUpdateCache" />Update Cache</label>
            <label class="checkbox-item">
                Select cache
                <select v-model="cacheStore.selectedCacheName">
                    <option v-for="(item, index) of cacheStore.cacheList.filter(cacheItem => {
                            return cacheItem.dataset_id === dataStore.selectedDatasetId && cacheItem.report_id === reportStore.selectedReportId;
                        })"
                        :key="index"
                    >
                        {{ item.name }}
                    </option>
                    <option disabled v-if="cacheStore.cacheList.filter(cacheItem => {
                            return cacheItem.dataset_id === dataStore.selectedDatasetId && cacheItem.report_id === reportStore.selectedReportId;
                        }).length === 0">No Cache Available</option>
                </select>
            </label>
        </div>
        <rs-button type="primary" @click="handleNewCache">+ Create New Cache</rs-button>
    </div>
</template>

<style lang="scss" scoped>
.cache-panel {
    display: flex;
    flex-direction: column;
    gap: 10px;

    .options {
        display: flex;
        flex-direction: v-bind(direction);
        gap: v-bind(gap);

        .checkbox-item {
            display: flex;
            gap: 6px;
            align-items: center;
        }   
    }

    select {
        width: 160px;
        border: 1px solid $bg-gray;
        border-radius: 5px;
        padding: 4px;
    }
}
</style>