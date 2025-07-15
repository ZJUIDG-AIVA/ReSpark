<script setup>
import { ref } from 'vue';
import { useReportStore } from '@/stores/report';
import BaseView from '@/components/view/BaseView.vue';
import CircularNodes from './CirularNodes/CircularNodes.vue';
import ReportNodes from './ReportNodes/ReportNodes.vue';

const mode = ref('analysis');

const reportStore = useReportStore();
</script>

<template>
    <base-view style="background-color: #eee; border: 1px solid #ffffff00;" width="30vw">
        <div class="row" v-if="reportStore.nodes">
            <circular-nodes class="node-panel" :mode="mode"></circular-nodes>
            <report-nodes class="node-panel" :mode="mode"></report-nodes>
        </div>
    </base-view>
</template>

<style lang="scss" scoped>
.row {
    display: flex;
    width: 100%;
    height: 100%;

    .node-panel:first-child {
        align-items: center;
        width: 33%;
    }

    .node-panel:last-child {
        width: 67%;
    }
}
</style>