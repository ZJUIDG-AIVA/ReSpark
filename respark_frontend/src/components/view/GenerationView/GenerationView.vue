<script setup>
import { ref } from 'vue';
import { useModeStore } from '@/stores/dependencyMode';
import { useGenerationStore } from '@/stores/generation';
import { useReportStore } from '@/stores/report';
import { useDataStore } from '@/stores/data';
import BaseView from '@/components/view/BaseView.vue';
import RsButton from '@/components/basic/RsButton.vue';

const modeStore = useModeStore();
const generationStore = useGenerationStore();
const reportStore = useReportStore();
const dataStore = useDataStore();

const collapseCode = ref(true);
const collapseTable = ref(true);

function handleApplyObjectiveResult() {
    reportStore.nodes.find(item => item.id === reportStore.selectedNodeId).analysis.question = generationStore.objectiveResult[reportStore.selectedNodeId].find(item => item.stage === 'Final Result').content.find(item => item.type === 'objective').objective;
    generationStore.objectiveResult[reportStore.selectedNodeId].find(item => item.stage === 'Final Result').content.find(item => item.type === 'data field')['data field'].forEach(fieldName => { dataStore.fields.find(item => item.column === fieldName).count += 1; });
    modeStore.target = 'content';
}

function handleApplyContentResult() {
    if (reportStore.nodes.find(item => item.id === reportStore.selectedNodeId).analysis.question){
        reportStore.indexToGenerate = reportStore.nodes.filter(node => node.analysis && node.analysis.question).indexOf(reportStore.nodes.find(item => item.id === reportStore.selectedNodeId)) + 1;
        reportStore.nodes.find(item => item.id === reportStore.selectedNodeId).content = [
            {
                type: 'text',
                text: generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'narration').content.map(item => item.text).join('')
            },
        ];
        if (generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'exe').content.find(item => item.type === 'image_url').image_url)
            reportStore.nodes.find(item => item.id === reportStore.selectedNodeId).content.push({
                type: 'image_url',
                image_url: generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'exe').content.find(item => item.type === 'image_url').image_url
            });
    } else {
        const currentNode = reportStore.nodes.find(item => item.id === reportStore.selectedNodeId);
        currentNode.content = [
            {
                type: 'text',
                text: generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'statement').content.map(item => item.text).join(''),
            },
        ];
        currentNode.summary = generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'summary').content.map(item => item.text).join('');
    }
}
</script>

<template>
    <base-view width="25vw" title="Generation View">
        <template #buttons>
            <div class="button-row">
                <rs-button :type="modeStore.target === 'objective' ? 'primary' : 'secondary'" @click="modeStore.target = 'objective'" :disabled="reportStore.nodes.find(node => node.id === reportStore.selectedNodeId) && !reportStore.nodes.find(node => node.id === reportStore.selectedNodeId).analysis.question">Objective</rs-button>
                <rs-button :type="modeStore.target === 'content' ? 'primary' : 'secondary'" :disabled="reportStore.nodes.find(node => node.id === reportStore.selectedNodeId) && !generationStore.objectiveResult[reportStore.selectedNodeId] && reportStore.nodes.find(node => node.id === reportStore.selectedNodeId).analysis.question" @click="modeStore.target = 'content'">Content</rs-button>
            </div>
        </template>
        <template #default v-if="modeStore.target === 'objective'">
            <div class="stage-list">
                <div class="stage" v-for="stage of generationStore.objectiveResult[reportStore.selectedNodeId]" :key="stage.stage">
                    <div class="status finished" v-if="stage.content.find(item => item.type === 'objective')">
                        <img src="/narration.svg" height="13" width="13" />
                        <span>Finish Generating Objective</span>
                        <img src="/finish.svg" height="13" width="13" />
                    </div>
                    <div class="status" v-else>
                        <img src="/narration_gray.svg" height="13" width="13" />
                        <span>Generating Objective</span>
                        <img class="loading" src="/loading.svg" height="13" width="13" />
                    </div>
                    <div class="name" v-if="stage.content.length > 0">{{ stage.stage }}</div>
                    <div class="text" v-if="stage.content.length > 0 && stage.content.find(item => item.type === 'text')">
                        {{ stage.content.find(item => item.type === 'text').text }}
                    </div>
                    <div class="object" v-if="stage.content.length > 0">
                        <div class="label" v-if="stage.content.find(item => item.type === 'objective')">
                            Analysis Objective
                        </div>
                        <div class="question" v-if="stage.content.find(item => item.type === 'objective')">
                            {{ stage.content.find(item => item.type === 'objective').objective }}
                        </div>
                        <div class="label" v-if="stage.content.find(item => item.type === 'data field') && stage.stage === 'Final Result'">
                            Involved Data Field
                        </div>
                        <div class="question" v-if="stage.content.find(item => item.type === 'data field') && stage.stage === 'Final Result'">
                            {{ stage.content.find(item => item.type === 'data field')['data field'].join(', ') }}
                        </div>
                    </div>
                </div>
            </div>
            <div class="button-row" v-if="generationStore.objectiveCompletedFlags.indexOf(reportStore.selectedNodeId) !== -1">
                <div class="flex-grow"></div>
                <rs-button type="secondary" @click="generationStore.doObjectiveGenerate(reportStore.selectedNodeId)">Regenerate</rs-button>
                <rs-button type="secondary" @click="handleApplyObjectiveResult">Apply</rs-button>
            </div>
        </template>
        <template #default v-else>
            <div class="stage-list" v-if="generationStore.contentResult[reportStore.selectedNodeId]">
                <div class="stage" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'code')">
                    <div class="status finished" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'exe')">
                        <img src="/narration.svg" height="13" width="13" />
                        <span>Finish Generating Code</span>
                        <img src="/finish.svg" height="13" width="13" />
                    </div>
                    <div class="status" v-else>
                        <img src="/narration_gray.svg" height="13" width="13" />
                        <span>Generating Code</span>
                        <img class="loading" src="/loading.svg" height="13" width="13" />
                    </div>
                    <highlightjs autodetect :code="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'code').content.map(codeSeg => codeSeg.code).join('')" :class="{ 'collapse': collapseCode }" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'code').content.map(codeSeg => codeSeg.code).join('')" />
                    <div class="collapse-button" @click="collapseCode = !collapseCode" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'code').content.map(codeSeg => codeSeg.code).join('')">{{ collapseCode ? 'Expand' : 'Collapse' }}</div>
                </div>
                <div class="stage" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'exe')">
                    <div class="status finished" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'narration')">
                        <img src="/narration.svg" height="13" width="13" />
                        <span>Finish Executing Code</span>
                        <img src="/finish.svg" height="13" width="13" />
                    </div>
                    <div class="status" v-else>
                        <img src="/narration_gray.svg" height="13" width="13" />
                        <span>Executing Code</span>
                        <img class="loading" src="/loading.svg" height="13" width="13" />
                    </div>
                    <table class="table" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'exe').content.find(item => item.type === 'table')">
                        <tr class="row">
                            <th v-for="(title, index) of generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'exe').content.find(item => item.type === 'table').table.order" :key="index">{{ title }}</th>
                        </tr>
                        <tr class="row" :class="{ gray: rowIndex % 2 }" v-for="(row, rowIndex) of JSON.parse(generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'exe').content.find(item => item.type === 'table').table.json).filter((_, index) => collapseTable ? index <= 2 : true)" :key="rowIndex">
                            <td v-for="(title, index) of generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'exe').content.find(item => item.type === 'table').table.order" :key="index">{{ row[title] }}</td>
                        </tr>
                    </table>
                    <div class="collapse-button" @click="collapseTable = !collapseTable" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'exe').content.find(item => item.type === 'table')">{{ collapseTable ? 'Expand' : 'Collapse' }}</div>
                    <img :src="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'exe').content.find(item => item.type === 'image_url').image_url" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'exe').content.find(item => item.type === 'image_url')" />
                </div>
                <div class="stage" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'narration')">
                    <div class="status finished" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'used_fields')">
                        <img src="/narration.svg" height="13" width="13" />
                        <span>Finish Generating Narration</span>
                        <img src="/finish.svg" height="13" width="13" />
                    </div>
                    <div class="status" v-else>
                        <img src="/narration_gray.svg" height="13" width="13" />
                        <span>Generating Narration</span>
                        <img class="loading" src="/loading.svg" height="13" width="13" />
                    </div>
                    <div class="narration">
                        {{ generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'narration').content.map(item => item.text).join('') }}
                    </div>
                </div>
                <div class="stage" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'statement')">
                    <div class="status finished" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'summary')">
                        <img src="/narration.svg" height="13" width="13" />
                        <span>Finish Generating Statement</span>
                        <img src="/finish.svg" height="13" width="13" />
                    </div>
                    <div class="status" v-else>
                        <img src="/narration_gray.svg" height="13" width="13" />
                        <span>Generating Statement</span>
                        <img class="loading" src="/loading.svg" height="13" width="13" />
                    </div>
                    <div class="narration">
                        {{ generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'statement').content.map(item => item.text).join('') }}
                    </div>
                </div>
                <div class="stage" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'summary')">
                    <div class="status finished" v-if="generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'imitate_result')">
                        <img src="/narration.svg" height="13" width="13" />
                        <span>Finish Generating Summary</span>
                        <img src="/finish.svg" height="13" width="13" />
                    </div>
                    <div class="status" v-else>
                        <img src="/narration_gray.svg" height="13" width="13" />
                        <span>Generating Summary</span>
                        <img class="loading" src="/loading.svg" height="13" width="13" />
                    </div>
                    <div class="narration">
                        {{ generationStore.contentResult[reportStore.selectedNodeId].find(stage => stage.stage === 'summary').content.map(item => item.text).join('') }}
                    </div>
                </div>
            </div>
            <div class="button-row" v-if="generationStore.contentCompletedFlags.indexOf(reportStore.selectedNodeId) !== -1">
                <div class="flex-grow"></div>
                <rs-button type="secondary" @click="generationStore.doContentGenerate(reportStore.selectedNodeId)">Regenerate</rs-button>
                <rs-button type="secondary" @click="handleApplyContentResult">Apply</rs-button>
            </div>
        </template>
    </base-view>
</template>

<style lang="scss" scoped>
.collapse * {
    max-height: 300px;
}

.collapse-button {
    cursor: pointer;
    margin-left: calc(50% - 50px);
    width: 100px;
    text-align: center;
    color: rgb(56, 74, 140);
    font-size: 12px;
    margin-top: -10px;
    border: 1px solid #dddddd;
    background-color: white;
    z-index: 100;
}

@keyframes spin {
    0% {
        transform: rotate(0deg);
    }
    100% {
        transform: rotate(360deg);
    }
}

.button-row {
    display: flex;
    gap: 5px;

    .flex-grow {
        flex-grow: 1;
    }
}

.stage-list {
    display: flex;
    flex-direction: column;
    margin-top: -15px;
    gap: 5px;

    .stage {
        display: flex;
        flex-direction: column;
        padding: 10px;
        gap: 10px;

        .status {
            display: flex;
            flex-direction: row;
            align-items: center;
            gap: 5px;
            font-size: 12px;
            color: rgb(67, 67, 67);

            .loading {
                animation: spin 1s linear infinite;
            }
        }

        .status.finished {
            color: $bg-primary;
        }

        .name {
            padding: 5px 10px;
            width: 100%;
            border-radius: 5px;
            color: $bg-primary;
            background-color: rgba(56, 74, 140, 0.2);
            font-size: 12px;
            font-weight: bolder;
        }

        .text {
            color: rgb(67, 67, 67);
            font-size: 12px;
        }

        .object {
            display: flex;
            flex-direction: column;
            background-color: #f5f6f9;
            border-radius: 5px;
            padding: 10px;
            gap: 5px;
            font-size: 12px;

            .label {
                color: rgb(56, 74, 140);
            }

            .question {
                font-weight: bolder;
            }
        }

        pre {
            font-size: 11px;
            line-height: 14px;

            ::-webkit-scrollbar {
                height: 4px;
                width: 4px;
            }

            ::-webkit-scrollbar-track {
                background: rgb(179, 177, 177);
                border-radius: 10px;
            }

            ::-webkit-scrollbar-thumb {
                background: rgb(136, 136, 136);
                border-radius: 10px;
            }

            ::-webkit-scrollbar-thumb:hover {
                background: rgb(100, 100, 100);
                border-radius: 10px;
            }

            ::-webkit-scrollbar-thumb:active {
                background: rgb(68, 68, 68);
                border-radius: 10px;
            }
        }

        .table {
            border: 1px solid #d2d3d99f;
            width: 100%;
            font-size: 12px;
            line-height: 14px;
            border-collapse: collapse;

            .row {
                color: rgb(67, 67, 67);
                font-weight: bolder;

                &.gray, &:first-child {
                    background-color: #f5f6f9;
                }

                th, td {
                    border: 1px solid #d2d3d99f;
                    padding: 3px;
                    text-align: center;
                }
            }
        }

        .narration {
            color: rgb(67, 67, 67);
            font-size: 12px;
            background-color: #f8f8f8;
            padding: 5px;
        }
    }
}
</style>