<script setup>
import { ref, watch } from 'vue';
import { useDataStore } from '@/stores/data';
import BaseView from '@/components/view/BaseView.vue';
import RsButton from '@/components/basic/RsButton.vue';

const showData = ref(false);
const dataStore = useDataStore();

const showDetail = ref(new Array(dataStore.fields.length).fill(false));

function toggleViewData () {
    if (!dataStore.isDataUploaded)
        return;
    showData.value = !showData.value;
}

watch(() => dataStore.isDataUploaded, (newVal) => {
    if (newVal)
        showData.value = true;
});
</script>

<template>
    <base-view title="Data View" width="20vw">
        <template #buttons>
            <rs-button type="secondary" @click="toggleViewData" :disabled="!dataStore.isDataUploaded">View Data</rs-button>
        </template>
        <template #default>
            <div class="view-content" v-if="showData">
                <div class="text-area title">{{ dataStore.fileName }}</div>
                <div class="sub-title">Dataset Information</div>
                <div class="text-area description">{{ dataStore.description }}</div>
                <div class="sub-title">Data Fields</div>
                <div class="field-table">
                    <div class="row" v-for="(item, index) of dataStore.fields" :key="index">
                        <img src="/right.svg" @click="showDetail[index] = true" v-if="!showDetail[index]" />
                        <img src="/down.svg" @click="showDetail[index] = false" v-else />
                        <div class="column-item first">
                            <span clsas="column-name">{{ item.column }}</span>
                            <span class="type">{{ item.properties.dtype }}</span>
                        </div>
                        <div class="column-item">
                            <span class="description">{{ item.properties.description }}</span>
                            <span class="type" v-if="showDetail[index]">{{ item.properties.num_unique_values }} unique values</span>
                            <span class="type" v-if="showDetail[index]">{{ item.properties.samples.join(', ') + '...' }}</span>
                        </div>
                        <div class="flex-grow"></div>
                        <div class="count" :class="{ emph: item.count > 0 }">{{ item.count }}</div>
                    </div>
                </div>
            </div>
        </template>
    </base-view>
</template>

<style lang="scss" scoped>
.view-content {
    display: flex;
    flex-direction: column;
    gap: 10px;

    .sub-title {
        font-size: 15px;
        color: $bg-primary;
    }

    .text-area {
        background-color: #00000008;
        padding: 5px;
        border-radius: 5px;
        font-size: 11px;
    }

    .text-area.title {
        color: black;
    }

    .text-area.description {
        color: #5c5c5c;
    }

    .field-table {
        display: flex;
        flex-direction: column;
        gap: 2px;
        font-size: 11px;
        width: 100%;

        .row {
            display: flex;
            background-color: #00000008;
            align-items: center;
            gap: 5px;
            width: 100%;

            img {
                height: 7px;
                width: 7px;
                margin-left: 8px;
            }

            div {
                padding: 3px 8px;
            }

            .column-item {
                display: flex;
                flex-direction: column;

                .column-name {
                    color: black;
                    font-size: 11px;
                }

                .type {
                    color: #5c5c5c;
                    font-size: 9px;
                }
            }

            .column-item.first {
                width: 70px;
                min-width: 70px;
                max-width: 70px;
            }

            .description {
                text-align: left;
                text-wrap: wrap;
            }

            .flex-grow {
                flex-grow: 1;
            }

            .count {
                padding: 0;
                box-sizing: border-box;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0px 10px;
                height: 100%;
                border-width: 0px 2px 0px 2px;
                border-style: solid;
                border-color: #FFFFFF;
                vertical-align: center;
                text-align: center;
            }

            .count.emph {
                background: rgba(0, 0, 0, 0.06);
            }
        }
    }
}
</style>