<script setup>
const model = defineModel();

function update() {
    model.value = false;
}
</script>

<template>
    <div class="rs-dropdown" v-show="model" @mouseleave="update">
        <slot></slot>
    </div>
</template>

<style lang="scss" scoped>
.rs-dropdown {
    width: fit-content;
    display: flex;
    flex-direction: column;
    background-color: white;
    border-radius: 20px;
    padding: 10px 20px;
    gap: 10px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
}
</style>