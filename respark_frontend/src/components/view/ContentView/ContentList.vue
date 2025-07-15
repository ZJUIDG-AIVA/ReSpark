<script setup>
import { useReportStore } from '@/stores/report';
import { useModeStore } from '@/stores/dependencyMode';
import { useLogger } from '@/logger';
import ContentNode from './ContentNode.vue';

const logger = useLogger();
const reportStore = useReportStore();
const modeStore = useModeStore();

function handleTextChange (newText, index) {
    for (let node of reportStore.nodes)
        if (node.id === reportStore.selectedNodeId)
            node.content[index].text = newText;
}
</script>

<template>
    <div class="list" v-if="modeStore.mode === 'analysis'">
        <content-node
            :type="item.type"
            :content="item.text || item.image_path || item.image_url"
            :highlights="reportStore.nodes.find(node => node.id === reportStore.selectedNodeId).highlights || []"
            @change="(newText) => { handleTextChange(newText, index); logger.log('Manually edited content: ' + reportStore.selectedNodeId); }"
            v-for="(item, index) of reportStore.nodes.find(node => node.id === reportStore.selectedNodeId).content"
            :key="index"
        />
    </div>
    <div class="list" v-else>
        <div class="list" v-for="node of reportStore.nodes" :key="node.id">
            <content-node
                :node-id="node.id"
                :is-header="node.type === 'header'"
                :type="item.type"
                :content="item.text || item.image_path || item.image_url"
                :highlights="node.highlights || []"
                @change="(newText) => { handleTextChange(newText, index); logger.log('Manually edited ' + node.type + ' node content: ' + node.id); }"
                v-for="(item, index) of node.content"
                :key="index"
            />
        </div>
    </div>
</template>

<style lang="scss" scoped>
.list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}
</style>