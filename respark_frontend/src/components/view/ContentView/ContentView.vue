<script setup>
import { ref, watch } from 'vue';

import { useReportStore } from '@/stores/report';
import { useDataStore } from '@/stores/data';
import { useModeStore } from '@/stores/dependencyMode';
import { useGenerationStore } from '@/stores/generation';
import BaseView from '@/components/view/BaseView.vue';
import RsButton from '@/components/basic/RsButton.vue';
import RsDialog from '@/components/basic/RsDialog.vue';
import ContentList from './ContentList.vue';
import { useLogger } from '@/logger';

const logger = useLogger();

const reportStore = useReportStore();
const dataStore = useDataStore();
const modeStore = useModeStore();
const generationStore = useGenerationStore();

const selectedFields = ref([]);
const selectedLogic = ref('');
const selectedFromNode = ref('Data');

const showLogicDialog = ref(false);
const showFieldsDialog = ref(false);
const showFromDialog = ref(false);

watch(() => dataStore.fields, (newVal) => {
    selectedFields.value = newVal.map(() => false);
});

const logicList = ['Initial', 'Similarity', 'Temporal', 'Contrast', 'Cause-Effect', 'Elaboration', 'Generalization'];
</script>

<template>
    <rs-dialog title="Select Logic" :visible="showLogicDialog" @submit="showLogicDialog = false" :show-cancel="false">
        <select class="select" v-model="selectedLogic">
            <option v-for="(logic, logicIndex) of logicList" :key="logicIndex">{{ logic }}</option>
        </select>
    </rs-dialog>
    <rs-dialog title="Select Parent Node" :visible="showFromDialog" @submit="showFromDialog = false" :show-cancel="false">
        <select class="select" v-model="selectedFromNode">
            <option v-for="nodeIndex of new Array(reportStore.nodes.filter((node, _index) => node.analysis && node.analysis.question && _index < reportStore.nodes.findIndex(node => node.id === reportStore.selectedNodeId)).length).fill().map((_, index) => index + 1).concat('-1')" :key="nodeIndex">{{ nodeIndex === '-1' ? 'Data' : nodeIndex }}</option>
        </select>
    </rs-dialog>
    <rs-dialog title="Select Fields" :visible="showFieldsDialog" @submit="showFieldsDialog = false" :show-cancel="false">
        <label class="checkbox-item" v-for="(item, index) of dataStore.fields" :key="index">
            <input type="checkbox" v-model="selectedFields[index]" />
            {{ item.column }}
        </label>
    </rs-dialog>
    <base-view width="25vw" title="Content View">
        <template #buttons>
            <div class="button-row">
                <rs-button type="secondary" @click="reportStore.restore">Restore</rs-button>
                <!-- <rs-button type="secondary">Save</rs-button> -->
                <rs-button type="secondary" @click="(modeStore.target === 'objective' ? generationStore.doObjectiveGenerate : generationStore.doContentGenerate)(reportStore.selectedNodeId, selectedFields.map((_, index) => dataStore.fields[index].column).filter((_, index) => selectedFields[index]), selectedLogic, selectedFromNode === 'Data' ? '-1' : reportStore.nodes.filter(node => node.analysis && node.analysis.question)[selectedFromNode - 1].id, () => { modeStore.target = 'content'; selectedFields.forEach((item, index) => { if (item) dataStore.fields[index].count += 1; }) })">Generate</rs-button>
            </div>
        </template>
        <template #default v-if="reportStore.selectedNodeId && reportStore.nodes.length && modeStore.mode === 'analysis'">
            <div class="analysis-object" v-if="reportStore.nodes.find(item => item.id === reportStore.selectedNodeId) && reportStore.nodes.find(item => item.id === reportStore.selectedNodeId).analysis.question && reportStore.nodesForRestore.find(item => item.id === reportStore.selectedNodeId)">
                <div class="label">Analysis Objective</div>
                <div class="question" :contenteditable="true" @blur="($event) => { reportStore.nodes.find(item => item.id === reportStore.selectedNodeId).analysis.question = $event.target.textContent; logger.log(`Manually edit analysis objective of node ${reportStore.selectedNodeId}`); }">{{ reportStore.nodes.filter(item => item.id === reportStore.selectedNodeId)[0].analysis.question }}</div>
            </div>
            <div class="analysis-object" v-else-if="reportStore.nodesForRestore.find(item => item.id === reportStore.selectedNodeId)">
                <div class="label">Summary</div>
                <div class="question">{{ reportStore.nodes.find(item => item.id === reportStore.selectedNodeId).summary }}</div>
            </div>
            <div class="analysis-object" v-else>
                <div class="label">Analysis Objective</div>
                <div class="question">No previous objective. Select and generate. </div>
                <div class="box-row">
                    <div class="box">
                        <div class="title-row">
                            <img src="/down.svg" />
                            <div class="title">Logic</div>
                        </div>
                        <div class="tags">
                            <div class="tag" v-if="selectedLogic">{{ selectedLogic }}</div>
                            <div class="tag" @click="showLogicDialog = true">Select...</div>
                        </div>
                    </div>
                    <div class="box">
                        <div class="title-row">
                            <img src="/down.svg" />
                            <div class="title">Formed from</div>
                        </div>
                        <div class="tags">
                            <div class="tag" v-if="selectedFromNode">{{ selectedFromNode }}</div>
                            <div class="tag" @click="showFromDialog = true">Select...</div>
                        </div>
                    </div>
                </div>
                <div class="box-row">
                    <div class="box">
                        <div class="title-row">
                            <img src="/down.svg" />
                            <div class="title">Data Field</div>
                        </div>
                        <div class="tags">
                            <div class="tag" v-for="(tag, tagIndex) of selectedFields.map((_, index) => dataStore.fields[index].column).filter((_, index) => selectedFields[index])" :key="tagIndex">{{ tag }}</div>
                            <div class="tag" @click="showFieldsDialog = true">Select...</div>
                        </div>
                    </div>
                </div>
            </div>
            <content-list></content-list>
        </template>
        <template #default v-else-if="reportStore.nodes.length && modeStore.mode === 'structure'">
            <content-list></content-list>
        </template>
    </base-view>
</template>

<style lang="scss" scoped>
.select {
    width: 160px;
    border: 1px solid $bg-gray;
    border-radius: 5px;
    padding: 4px;
}

.checkbox-item {
    display: flex;
    align-items: center;
    gap: 6px;
}

.button-row {
    display: flex;
    gap: 5px;
}

.analysis-object {
    display: flex;
    flex-direction: column;
    background-color: #f5f6f9;
    border: 1px solid #dddddd;
    border-radius: 5px;
    padding: 10px;
    gap: 5px;

    .label {
        color: rgb(56, 74, 140);
        font-size: 15px;
    }

    .question {
        font-weight: bolder;
        font-size: 12px;
    }

    .box-row {
        display: flex;
        width: 100%;
        gap: 10px;

        .box {
            display: flex;
            flex-direction: column;
            width: 100%;
            border: 1px solid #DADADA;
            border-radius: 5px;
            padding: 5px;
            gap: 10px;

            .title-row {
                display: flex;
                align-items: center;
                gap: 5px;

                img {
                    width: 8px;
                    height: 8px;
                }

                .title {
                    font-style: normal;
                    font-weight: 700;
                    font-size: 12px;
                    line-height: 14px;
                    color: #676767;
                }
            }

            .tags {
                display: flex;
                flex-wrap: wrap;
                width: 100%;
                max-width: 100%;
                gap: 5px;
                align-items: center;

                .tag {
                    font-size: 10px;
                    padding: 2px 10px;
                    background: #C2C8DC;
                    border-radius: 8px;
                    font-weight: 400;
                    font-size: 10px;
                    line-height: 12px;
                    text-align: center;
                }
            }
        }
    }
}
</style>

<style>
code {
    font-family: 'Source Code Pro';
}
</style>