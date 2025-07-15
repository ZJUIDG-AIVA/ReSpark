<script setup>
import { ref } from 'vue';
import { useModeStore } from '@/stores/dependencyMode.js';
import { useReportStore } from '@/stores/report';
import { useGenerationStore } from '@/stores/generation';
import RsButton from '@/components/basic/RsButton.vue';
import ParaNode from './ParaNode.vue';
import HeaderNode from './HeaderNode.vue';

const modeStore = useModeStore();
const reportStore = useReportStore();
const generationStore = useGenerationStore();

const rightSelectedNode = ref([-1, -2]);

const isLoading = ref({});

function handleRightSelection(index) {
    if (rightSelectedNode.value[0] > rightSelectedNode.value[1]) {
        rightSelectedNode.value[0] = index;
        rightSelectedNode.value[1] = index;
    } else if (index < rightSelectedNode.value[0])
        rightSelectedNode.value[0] = index;
    else if (index > rightSelectedNode.value[1])
        rightSelectedNode.value[1] = index;
    else if (index === rightSelectedNode.value[0])
        rightSelectedNode.value[0]++;
    else if (index === rightSelectedNode.value[1])
        rightSelectedNode.value[1]--;
}

function handleClickFloatButton(index, parentId) {
    if (index === 1)
        reportStore.addParaNode(parentId);
    else if (index === 0)
        reportStore.deleteParaNode(parentId);
    else {
        const prevIndex = reportStore.nodes.findIndex(node => node.id === parentId) - 1;
        reportStore.addParaNode(reportStore.nodes[prevIndex].id);
    }
}

function handleAddTitle() {
    reportStore.addHeaderNode(rightSelectedNode.value[0], rightSelectedNode.value[1]);
    rightSelectedNode.value = [-1, -2];
}

function handleSelectReportNode(id) {
    reportStore.selectedNodeId = id;
    if (!generationStore.objectiveResult[id] && modeStore.target === 'content')
        modeStore.target = 'objective';
    if (reportStore.nodes.find(item => item.id === id).matchType === 'Unmatched')
        modeStore.target = 'content';
}
</script>

<template>
    <div class="container">
        <div class="button-row">
            <div class="flex-grow"></div>
            <rs-button :type="modeStore.mode === 'analysis' ? 'primary' : 'secondary'" @click="modeStore.mode = 'analysis'">Analysis mode</rs-button>
            <rs-button :type="modeStore.mode === 'structure' ? 'primary' : 'secondary'" @click="modeStore.mode = 'structure'">Structure mode</rs-button>
        </div>
        <div class="para-node-list" v-if="modeStore.mode === 'analysis'">
            <para-node
                :key="item.id"
                :title="item.analysis.question || item.summary"
                :match-type="item.matchType"
                :text="item.content[0].text"
                :image="item.content.length > 1 ? item.content[1][item.content[1].type] : ''"
                :selected="reportStore.selectedNodeId === item.id"
                :float-buttons="['- Delete', '+ Insert After', '+ Insert Before']"
                :indent="0"
                @click-float-button="(buttonIndex) => { handleClickFloatButton(buttonIndex, item.id) }"
                @update-selection="handleSelectReportNode(item.id)"
                v-for="item of reportStore.nodes.filter(_item => _item.type === 'paragraph')"
            />
        </div>
        <div class="para-node-list" v-else>
            <div
                :key="item.id"
                v-for="(item, index) of reportStore.nodes"
                :style="{ 
                    width: item.type === 'paragraph' ? `calc(100% - 20px * ${reportStore.indents[item.id] || 0})` : `calc(100% - 20px * ${reportStore.indents[reportStore.nodes[index ? index : 0].id] || 0})`
                }
            ">
                <para-node
                    :title="item.analysis.question || item.summary"
                    :match-type="item.matchType"
                    :summary="item.sumamry"
                    :text="item.content[0].text"
                    :image="item.content.length > 1 ? item.content[1].image_path : ''"
                    :selected="reportStore.selectedNodeId === item.id"
                    :float-buttons="rightSelectedNode[0] <= index && rightSelectedNode[1] >= index ? ['Add title'] : []"
                    :indent="0"
                    :right-selectable="true"
                    :right-selected="rightSelectedNode[0] <= index && rightSelectedNode[1] >= index"
                    @click-float-button="handleAddTitle"
                    @update-right-selection="handleRightSelection(index)"
                    @update-selection="handleSelectReportNode(item.id)"
                    v-if="item.type === 'paragraph'"
                />
                <header-node
                    :indent="0"
                    :title="item.content[0].text"
                    :loading="isLoading[item.id]"
                    @click-generate="() => { reportStore.handleGenerateTitle(item.id, () => { isLoading[item.id] = false; }); isLoading[item.id] = true; }"
                    @click-delete="reportStore.deleteHeaderNode(item.id)"
                    v-else
                />
            </div>
            <div
                class="segment"
                :style="{
                    height: reportStore.nodes.filter(node => item.childrenNode.indexOf(node.id) !== -1)
                            .map(node => node.type === 'header' ? 90 : 110)
                            .reduce((acc, val) => acc + val, 0) + 'px',
                    left: (reportStore.indents[item.id] || 0) * 20 + 5 + 'px',
                    top: reportStore.nodes.slice(0, reportStore.nodes.indexOf(item))
                            .map(node => node.type === 'header' ? 90 : 110)
                            .reduce((acc, val) => acc + val, 0) + 80 + 'px'
                }"
                :key="item.id"
                v-for="item of reportStore.nodes.filter(node => node.type === 'header')"
            >
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.flex-grow {
    flex-grow: 1;
}

.container {
    display: flex;
    flex-direction: column;
    justify-self: center;
    gap: 20px;

    .button-row {
        display: flex;
        flex-direction: row;
        gap: 20px;
    }

    .para-node-list {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 10px;
        padding-bottom: 15px;

        .segment {
            position: absolute;
            width: 1px;
            background-color: #384a8c;
        }
    }
}
</style>