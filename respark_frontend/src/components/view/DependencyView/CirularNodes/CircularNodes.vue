<script setup>
import { onMounted, watch } from 'vue';
import { useReportStore } from '@/stores/report';
import { useModeStore } from '@/stores/dependencyMode';
import TooltipCanvasDrawer from './canvasDrawer';
import RsButton from '@/components/basic/RsButton.vue';

const reportStore = useReportStore();
const modeStore = useModeStore();

const initialHeight = reportStore.nodes.filter(item => item.type === 'paragraph').length * 110 + 10;

function drawNodes() {
    reportStore.indents;
    const drawer = TooltipCanvasDrawer(document.getElementById('node-canvas'));
    let nodePosition = {};

    for (let nodeId in reportStore.nodeDepth) {
        let nodeIndex;
        for (nodeIndex = 0; nodeIndex < reportStore.nodes.length; ++nodeIndex)
            if (reportStore.nodes[nodeIndex].id === nodeId)
                break;
        nodePosition[nodeId] = {
            x: reportStore.position[nodeId].left + reportStore.position[nodeId].width / 2,
            y: (nodeIndex - (reportStore.numberOfTitlesBeforeNode[nodeId] || 0)) * 110 + 50 + 50 + 90 * (reportStore.numberOfTitlesBeforeNode[nodeId] || 0) * (modeStore.mode === 'structure')
        };
    }
    nodePosition['-1'] = {
        x: 65,
        y: 0
    };

    for (let edge of reportStore.edges) {
        drawer.drawCurve({
            startX: nodePosition[edge.fromId].x,
            startY: nodePosition[edge.fromId].y,
            cp1X: nodePosition[edge.fromId].x,
            cp1Y: 0.5 * (nodePosition[edge.fromId].y + nodePosition[edge.toId].y),
            cp2X: nodePosition[edge.toId].x,
            cp2Y: 0.5 * (nodePosition[edge.fromId].y + nodePosition[edge.toId].y),
            endX: nodePosition[edge.toId].x,
            endY: nodePosition[edge.toId].y,
            tooltipText: edge.relation
        });
    }

    for (let [nodeId, ] of Object.entries(reportStore.nodeDepth)) {
        if (nodeId === '-1')
            continue;
        const currentIndex = reportStore.nodes.filter(node => node.analysis && node.analysis.question).indexOf(reportStore.nodes.find(item => item.id === nodeId));
        const currentNode = reportStore.nodes.find(item => item.id === nodeId);
        drawer.drawCircle({
            x: nodePosition[nodeId].x,
            y: nodePosition[nodeId].y,
            r: 10,
            tooltipText: currentIndex + 1 + '',
            text: currentNode.analysis && currentNode.analysis.question === 'None' ? 'X' : currentIndex + 1 + '',
            strokeColor: currentNode.analysis && currentNode.analysis.question === 'None' ? '#AA3333': (currentIndex <= reportStore.indexToGenerate ? '#384A8C' : '#9E9E9E'),
            fillColor: currentNode.analysis && currentNode.analysis.question === 'None' ? '#AA3333' : (currentIndex < reportStore.indexToGenerate ? '#384A8C' : currentIndex === reportStore.indexToGenerate ? '#959EBF' : '#9E9E9E'),
        })
    }
}

onMounted(drawNodes);
watch(() => reportStore.nodes, drawNodes, { deep: true });
watch(() => reportStore.edges, drawNodes, { deep: true });
watch(() => modeStore.mode, drawNodes);
</script>

<template>
    <div class="container">
        <rs-button type="primary" style="z-index: 5;" :disabled="!reportStore.nodes.length">Data</rs-button>
        <canvas
            id="node-canvas"
            :height="initialHeight"
            width="130">
        </canvas>
    </div>
</template>

<style lang="scss" scoped>
.container {
    display: flex;
    flex-direction: column;
    justify-self: center;
    gap: 20px;
    position: relative;

    #node-canvas {
        position: absolute;
        z-index: 1;
    }
}
</style>