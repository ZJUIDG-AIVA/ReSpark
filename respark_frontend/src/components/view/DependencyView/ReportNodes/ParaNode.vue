<script setup>
import { ref } from 'vue';

const props = defineProps(['selected', 'rightSelected', 'rightSelectable', 'floatButtons', 'title', 'text', 'image', 'indent', 'matchType', 'summary']);
const emits = defineEmits(['updateSelection', 'updateRightSelection', 'clickFloatButton']);

const showFloatList = ref(false);
const width = `calc(100% - ${props.indent} * 20px)`;

function handleRightClick() {
    if (!props.rightSelectable)
        return;
    emits('updateRightSelection');
}
</script>

<template>
    <div class="para-node" :class="{ selected: props.selected, 'right-selected': props.rightSelected, unmatched: props.matchType === 'Unmatched' }" @click="$emit('updateSelection')" @contextmenu.prevent="handleRightClick" @mouseenter="showFloatList = true" @mouseleave="showFloatList = false">
        <div class="para-node-inner">
            <div class="title">{{ props.title || props.summary }}</div>
            <div class="content">
                <div class="text-content">{{ props.text }}</div>
                <img class="image-content" :src="props.image" v-if="props.image" />
            </div>
        </div>
        <div class="float-button-list" v-if="showFloatList">
            <div class="button" v-for="(item, index) of props.floatButtons" :key="index" @click.stop="$emit('clickFloatButton', index)">{{ item }}</div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.para-node {
    display: flex;
    flex-direction: column;
    border-radius: 5px;
    padding: 7px;
    box-sizing: border-box;
    border: 1px solid #2c3d83;
    height: 100px;
    width: v-bind(width);
    position: relative;

    .para-node-inner {
        height: 100%;
        width: 100%;
        overflow-y: auto;
        scrollbar-width: none;

        .title {
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .content {
            display: flex;
            gap: 10px;
            width: 100%;

            .text-content {
                font-size: 11px;
                color: #888888;
            }

            .image-content {
                width: 30%;
                height: fit-content;
            }
        }
    }
}

.para-node.unmatched {
    border: 1px solid #2c3d835c;
}

.para-node.selected {
    background-color: white;
}

.para-node.right-selected {
    box-shadow: rgba(21, 35, 71, 0.827) 0px 0px 5px;
}

.float-button-list {
    display: flex;
    justify-content: center;
    position: absolute;
    bottom: -8px;
    width: 100%;
    gap: 20px;

    .button {
        border: 1px solid #c5c7ce;
        background-color: white;
        border-radius: 3px;
        box-sizing: border-box;
        padding: 0px 3px;
        font-size: 10px;
        color: #515152;
        cursor: pointer;
    }
}
</style>