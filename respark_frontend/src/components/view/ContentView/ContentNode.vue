<script setup>
import { ref, onMounted, nextTick, watch } from 'vue';
import { useReportStore } from '@/stores/report';

const props = defineProps(['type', 'content', 'isHeader', 'nodeId', 'highlights']);
const emits = defineEmits(['change']);
const reportStore = useReportStore();

const showButtons = ref(false);
const editableContent = ref('');

function highlightText(content, highlights) {
    let highlightedContent = content;
    for (let i = 0; i < highlights.length; i++) {
        const text = highlights[i].text;
        highlightedContent = highlightedContent.replace(text, `<span class="highlight" style="background-color: #cccccc91; cursor: pointer; ">${text}</span>`);
    }
    return highlightedContent;
}

function handleTextChange(e) {
    const rawText = e.target.innerText;
    if (props.nodeId) {
        reportStore.selectedNodeId = props.nodeId;
    }
    emits('change', rawText);
}

onMounted(() => {
    nextTick(() => {
        editableContent.value = highlightText(props.content, props.highlights);
    });
});

watch(() => props.content, () => {
    editableContent.value = highlightText(props.content, props.highlights);
});
</script>

<template>
    <div class="wrapper" @mouseenter="showButtons = true" @mouseleave="showButtons = false">
        <div
            :class="{ header: props.isHeader }"
            v-if="props.type === 'text'"
            v-html="editableContent"
            contenteditable="true"
            @blur="handleTextChange"
        ></div>
        <img :src="props.content" v-else-if="props.type === 'image_path' || props.type === 'image_url'" />
        <div class="button-column" v-show="showButtons">
            <img class="button" src="/move.svg" />
            <img class="button" src="/add.svg" />
            <img class="button" src="/delete.svg" />
        </div>
    </div>
</template>

<style lang="scss" scoped>
.wrapper {
    display: flex;
    flex-direction: row-reverse;
    justify-content: flex-start;
    width: 100%;
    border-radius: 5px;
    padding: 5px;
    gap: 5px;

    .button-column {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        padding-top: 5px;

        img {
            height: 12px;
            width: fit-content;
        }

        img:hover {
            cursor: pointer;
        }
    }

    [contenteditable] {
        min-height: 60px;
        width: 95%;
        padding: 2px;
        border-radius: 5px;
        font-size: 12px;
        font-family: "Trebuchet MS";
        color: #434343;
        outline: none;
        border: none;
        word-wrap: break-word;
    }

    .header[contenteditable] {
        font-weight: bold;
        font-size: 14px;
    }

    img {
        width: 95%;
        height: fit-content;
    }
}

.wrapper:hover {
    background-color: #f4f4f4;
}
</style>
