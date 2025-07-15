<script setup>
import { nextTick, ref, watch } from 'vue';
import { useCacheStore } from '@/stores/cache.js';
import { useDataStore } from '@/stores/data';
import { useReportStore } from '@/stores/report';
import { useDatabaseStore } from '@/stores/database';
import { useModeStore } from '@/stores/dependencyMode.js';
import { useGenerationStore } from '@/stores/generation';
import RsButton from '@/components/basic/RsButton.vue';
import RsDropdown from '@/components/basic/RsDropdown.vue';
import RsDialog from '@/components/basic/RsDialog.vue';
import RsTable from '@/components/basic/RsTable.vue';
import CachePanel from '@/components/topBar/CachePanel.vue';
import { convertSize } from '@/utils';
import { useLogger } from '@/logger';

const logger = useLogger();

const cacheStore = useCacheStore();
const dataStore = useDataStore();
const reportStore = useReportStore();
const databaseStore = useDatabaseStore();
const modeStore = useModeStore();
const generationStore = useGenerationStore();

const showDropdown = ref(false);

const showDataDialog = ref(false);
const showReportDialog = ref(false);
const searchText = ref('');

const isUploading = ref(false);
const currentFileName = ref('');

const isProcessing = ref(false);

const selectedRowIndex = ref(null);

function handleShowDropdown () {
    showDropdown.value = !showDropdown.value;
}

function handleShowDataDialog () {
    databaseStore.updateDatabase(() => { showDataDialog.value = true; });
}

function handleShowReportDialog () {
    fetch('http://localhost:5000/recommend_report', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            cache_path: cacheStore.selectedCacheName,
            use_cache: cacheStore.isUseCache,
            update_cache: cacheStore.isUpdateCache,
        })
    })
        .then(response => response.json())
        .then(data => {
            databaseStore.reports = data.map(item => { 
                return {
                    id: item.id,
                    name: item.name,
                    size: convertSize(item.size),
                    rawSize: item.size,
                    topic: item.topic,
                    predictedFields: item.predicted_fields.join(', '),
                }
            });
            showReportDialog.value = true;
        })
}

function handleSelectDataset () {
    dataStore.cacheFileName = databaseStore.datasets.filter(item => item.name.toLowerCase().includes(searchText.value.toLowerCase()))[selectedRowIndex.value].name;
    dataStore.selectedDatasetId = databaseStore.datasets.filter(item => item.name.toLowerCase().includes(searchText.value.toLowerCase()))[selectedRowIndex.value].id;
    fetch('http://localhost:5000/select_dataset', {
        method: 'POST',
        body: JSON.stringify({
            selected_id: databaseStore.datasets.filter(item => item.name.toLowerCase().includes(searchText.value.toLowerCase()))[selectedRowIndex.value].id,
            cache_path: cacheStore.selectedCacheName,
            use_cache: cacheStore.isUseCache,
            update_cache: cacheStore.isUpdateCache,
        }),
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => response.json())
        .then(data => {
            showDataDialog.value = false;
            dataStore.isDataUploaded = true;
            dataStore.fileName = data.file_name;
            dataStore.description = data.dataset_description;
            dataStore.fields = data.fields.map(item => {
                return {
                    ...item,
                    count: 0,
                };
            });
            logger.log('Select dataset: ' + dataStore.fileName);
        })
        .catch((err) => {
            console.error(err);
        });
}

function handleSelectReport () {
    isProcessing.value = true;
    reportStore.resetReport();
    reportStore.fileName = databaseStore.reports.filter(item => item.name.toLowerCase().includes(searchText.value.toLowerCase()))[selectedRowIndex.value].name;
    fetch('http://localhost:5000/select_report', {
        method: 'POST',
        body: JSON.stringify({
            selected_id: databaseStore.reports.filter(item => item.name.toLowerCase().includes(searchText.value.toLowerCase()))[selectedRowIndex.value].id,
            cache_path: cacheStore.selectedCacheName,
            use_cache: cacheStore.isUseCache,
            update_cache: cacheStore.isUpdateCache,
        }),
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => response.json())
        .then(data => {
            const result = JSON.parse(data.content[0].text);
            for (let node of result) {
                const convertedNode = {
                    id: node.id + '',
                    parentId: (node['formed from'] || '-1') + '',
                    level: 0,
                    type: node.match_type === 'header' ? 'header' : 'paragraph',
                    matchType: node.match_type.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
                    content: [
                        {
                            type: 'text',
                            text: typeof node.text === 'string' ? node.text : node.text.join('\n')
                        }
                    ],
                    summary: node.summary ? node.summary.join(' ') : null,
                    highlights: node.highlights ? node.highlights.content : [],
                };
                if (node.match_type === 'header') {
                    convertedNode.childrenNode = node.children_nodes.map(i => i + '');
                } else {
                    convertedNode.analysis = {
                        question: node['analysis question'],
                        operation: node['analysis operation']
                    };
                    if (node.image_url)
                        convertedNode.content.push({
                            type: 'image_url',
                            image_url: 'data:image/png;base64,' + node.image_url
                        });
                }
                convertedNode.dataSentences = node['data_sentences'] || [];
                convertedNode.nonDataSentences = node['non_data_sentences'] || [];
                convertedNode.highlights = convertedNode.nonDataSentences;
                reportStore.nodes.push(convertedNode);

                if (node['formed from'])
                    reportStore.edges.push({
                        fromId: node['formed from'] + '',
                        toId: node.id + '',
                        relation: node.logic,
                        description: node['logic description']
                    });
            }
            reportStore.nodesForRestore = JSON.parse(JSON.stringify(reportStore.nodes));
            reportStore.edgesForRestore = JSON.parse(JSON.stringify(reportStore.edges));
            isProcessing.value = false;
            showReportDialog.value = false;
            for (const node of reportStore.nodes)
                if (node.type !== 'header') {
                    reportStore.selectedNodeId = node.id;
                    break;
                }
            if (reportStore.nodes.find(item => item.id === reportStore.selectedNodeId).matchType === 'Unmatched')
                modeStore.target = 'content';
            reportStore.newId = reportStore.nodes.length + '';

            // Trigger repaint
            modeStore.mode = (modeStore.mode === 'structure' ? 'analysis' : 'structure');
            nextTick(() => { modeStore.mode = (modeStore.mode === 'structure' ? 'analysis' : 'structure'); });

            logger.log('Select report: ' + reportStore.fileName);
        })
        .catch((err) => {
            console.error(err);
            alert('Failed to select report');
            isProcessing.value = false;
            showReportDialog.value = false;
        });
}

function handleUploadData () {
    const input = document.getElementById('upload-data');
    input.click();
    if (input.onchange)
        return;
    input.addEventListener('change', () => {
        if (isUploading.value)
            return;
        isUploading.value = true;
        const file = input.files[0];
        currentFileName.value = file.name;
        const reader = new FileReader();
        reader.onload = () => {
            const formData = new FormData();
            formData.append('file', file);
            dataStore.uploadData(formData, () => { isUploading.value = false; databaseStore.updateDatabase(); showDataDialog.value = false; dataStore.fields = dataStore.fields.map(item => {
                return {
                    ...item,
                    count: 0,
                };
            }); });
        };
        reader.readAsText(file);
    });
}

function handleUploadFile () {
    const input = document.getElementById('upload-file');
    input.click();
    if (input.onchange)
        return;
    input.addEventListener('change', () => {
        if (isUploading.value)
            return;
        isUploading.value = true;
        const file = input.files[0];
        currentFileName.value = file.name;
        reportStore.fileName = file.name;
        const reader = new FileReader();
        reader.onload = () => {
            const formData = new FormData();
            formData.append('file', file);
            reportStore.uploadReport(formData, () => { isUploading.value = false; databaseStore.updateDatabase(); });
        };
        reader.readAsText(file);
    });
}

function handleImportJSON() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.click();
    input.addEventListener('change', () => {
        const file = input.files[0];
        const reader = new FileReader();
        reader.onload = () => {
            const data = JSON.parse(reader.result);
            reportStore.nodes = data.nodes;
            reportStore.edges = data.edges;
            reportStore.nodesForRestore = JSON.parse(JSON.stringify(reportStore.nodes));
            reportStore.edgesForRestore = JSON.parse(JSON.stringify(reportStore.edges));
            if (data.generation) {
                generationStore.objectiveResult = data.generation.objectiveResult;
                generationStore.contentResult = data.generation.contentResult;
                generationStore.objectiveCompletedFlags = data.generation.objectiveCompletedFlags;
                generationStore.contentCompletedFlags = data.generation.contentCompletedFlags;
            }
            if (data.data) {
                dataStore.isDataUploaded = true;
                dataStore.fileName = data.data.fileName;
                dataStore.cacheFileName = data.data.cacheFileName;
                dataStore.description = data.data.description;
                dataStore.fields = data.data.fields;
                dataStore.selectedDatasetId = data.data.selectedDatasetId;
            }
            if (data.reportInfo) {
                reportStore.fileName = data.reportInfo.fileName;
                reportStore.selectedReportId = data.reportInfo.selectedReportId;
                reportStore.indexToGenerate = data.reportInfo.indexToGenerate;
                reportStore.newId = data.reportInfo.newId;
                cacheStore.selectedCacheName = data.reportInfo.selectedCacheName;
            }
            // Trigger repaint
            modeStore.mode = (modeStore.mode === 'structure' ? 'analysis' : 'structure');
            nextTick(() => { modeStore.mode = (modeStore.mode === 'structure' ? 'analysis' : 'structure'); });
        };
        reader.readAsText(file);
    });
}

watch(showDataDialog, (newVal) => { if (newVal) searchText.value = '' });
</script>

<template>
    <rs-dialog title="Dataset" :visible="showDataDialog" @close="showDataDialog = false" @submit="handleSelectDataset" :pending="isUploading">
        <div class="dialog">
            <div class="sub-title">Upload Dataset</div>
            <div class="status" v-if="isUploading">
                Uploading {{ currentFileName }}...
                <img class="loading" width="10" height="10" src="/loading.svg" />
            </div>
            <div class="upload-area" @click="handleUploadData">
                Click here to upload dataset
                <input type="file" id="upload-data" style="display: none;" />
            </div>
            <div class="row">
                <div class="sub-title">Select Data</div>
                <div class="row" style="justify-content: flex-end;">
                    <span>Search:&nbsp;&nbsp;</span>
                    <input v-model="searchText" />
                </div>
            </div>
            <rs-table :columns="[
                { name: 'name', label: 'Name', sortable: true, showTooltip: true },
                { name: 'size', label: 'Size', sortable: true, showTooltip: false },
                { name: 'information', label: 'Information', sortable: false, showTooltip: true }, ]"
                :show-view-button="false"
                :data="databaseStore.datasets.filter(item => item.name.toLowerCase().includes(searchText.toLowerCase()))"
                v-if="databaseStore.datasets.length"
                @select="selectedRowIndex = $event"
            >
            </rs-table>
            <div class="empty" v-else>
                No Datasets
            </div>
        </div>
    </rs-dialog>
    <rs-dialog title="Report" :visible="showReportDialog" @close="showReportDialog = false" @submit="handleSelectReport" :pending="isProcessing">
        <div class="dialog">
            <div class="row">
                <div class="sub-title">Select Data</div>
                <div class="row" style="justify-content: flex-end;">
                    <span>Search:&nbsp;&nbsp;</span>
                    <input v-model="searchText" />
                </div>
            </div>
            <rs-table :columns="[
                { name: 'name', label: 'Name', sortable: true, showTooltip: true },
                { name: 'topic', label: 'Topic', sortable: true, showTooltip: false },
                { name: 'predictedFields', label: 'Predicted Fields', sortable: false, showTooltip: true },
                { name: 'size', label: 'Size', sortable: true, showTooltip: false }, ]"
                :show-view-button="true"
                :data="databaseStore.reports.filter(item => item.name.toLowerCase().includes(searchText.toLowerCase()))"
                @select="($event) => {  selectedRowIndex = $event; reportStore.fileName = databaseStore.reports.filter(item => item.name.toLowerCase().includes(searchText.toLowerCase()))[selectedRowIndex].name; reportStore.selectedReportId = databaseStore.reports.filter(item => item.name.toLowerCase().includes(searchText.toLowerCase()))[selectedRowIndex].id; cacheStore.selectedCacheName = ''; }"
            >
            </rs-table>
            <div class="sub-title">Upload Report</div>
            <div class="status" v-if="isUploading">
                Uploading {{ currentFileName }}...
                <img class="loading" width="10" height="10" src="/loading.svg" />
            </div>
            <div class="upload-area" @click="handleUploadFile">
                Click here to upload report
                <input type="file" id="upload-file" style="display: none;" />
            </div>
            <div class="sub-title">Cache Options</div>
            <cache-panel direction="row"></cache-panel>
            <div class="status" v-if="isProcessing">
                Processing current report...
                <img class="loading" width="10" height="10" src="/loading.svg" />
            </div>
        </div>
    </rs-dialog>
    <div class="component-container">
        <span class="title">ReSpark</span>
        <div class="flex-grow"></div>
        <rs-button type="secondary" @click="handleImportJSON">
            Import JSON
        </rs-button>
        <rs-button type="secondary" @click="reportStore.exportReport">
            Export JSON
        </rs-button>
        <rs-button type="secondary" @click="reportStore.exportHTML">
            Export HTML
        </rs-button>
        <rs-button type="secondary" @click="handleShowDataDialog">
            Upload Data
        </rs-button>
        <rs-button type="secondary" @click="handleShowReportDialog" :disabled="!dataStore.isDataUploaded">
            Retrieve Report
        </rs-button>
        <rs-button id="settings-button" type="secondary" @click="handleShowDropdown">Settings</rs-button>
        <rs-dropdown id="dropdown" v-model="showDropdown">
            <cache-panel></cache-panel>
        </rs-dropdown>
    </div>
</template>

<style lang="scss" scoped>
.component-container {
    display: flex;
    align-items: center;
    padding: 5px 20px;
    gap: 20px;
    background-color: $bg-primary;

    .title {
        color: white;
        font-size: 18px;
    }

    .flex-grow {
        flex-grow: 1;
    }

    #dropdown {
        position: absolute;
        top: 50px;
        right: 10px;
    }
}
</style>

<style lang="scss">
@keyframes spin {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}

.dialog {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
    width: 100%;

    .empty {
        font-size: 13px;
        text-align: center;
        color: #aaa;
        width: 400px;
        border: 1px solid #ddd;
        padding: 5px;
        border-radius: 5px;
    }

    .loading {
        animation: spin 1s linear infinite;
    }

    .row {
        width: 100%;
        display: flex;
        align-items: center;
        text-wrap: nowrap;
        align-items: center;

        input {
            width: 150px;
            background: #FFFFFF;
            border: 1px solid #DDDDDD;
            border-radius: 2px;
        }
    }

    .sub-title {
        font-weight: 700;
        font-size: 15px;
        line-height: 17px;
        color: #000000;
    }

    .status {
        display: flex;
        gap: 5px;
        align-items: center;
        font-size: 11px;
    }

    .upload-area {
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        box-sizing: border-box;
        height: 46px;
        width: 100%;
        background: #F5F6F9;
        border: 1px solid #DDDDDD;
        border-radius: 3px;
    }
}
</style>