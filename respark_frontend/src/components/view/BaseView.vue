<script setup>
import { computed } from 'vue';
const props = defineProps(['title', 'width']);
const width = computed(() => props.width);
</script>

<template>
    <div class="view-container">
        <div class="title-row" v-if="props.title">
            <div class="title">{{ props.title }}</div>
            <div class="flex-grow"></div>
            <slot name="buttons"></slot>
        </div>
        <slot name="default"></slot>
    </div>
</template>

<style lang="scss" scoped>
.view-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    max-height: 100%;
    overflow-y: auto;
    width: v-bind(width);
    padding: 15px;
    gap: 20px;
    box-sizing: border-box;
    scrollbar-width: none;
    border-left: 1px solid #e9e7e7b9;
    border-right: 1px solid #e9e7e7b9;

    .title-row {
        display: flex;
        align-items: center;

        .flex-grow {
            flex-grow: 1;
        }

        .title {
            font-size: 18px;
            color: $bg-primary;
        }
    }
}
</style>