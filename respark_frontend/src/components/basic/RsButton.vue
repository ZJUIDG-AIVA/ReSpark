<script setup>
const props = defineProps(['type', 'disabled']);
defineEmits(['click']);
</script>

<template>
    <div class="rs-button" :class="{
        disabled: props.disabled,
        primary: props.type === 'primary' && !props.disabled,
        secondary: props.type === 'secondary' && !props.disabled
    }" @click="() => { if (!props.disabled) $emit('click') }">
        <slot></slot>
    </div>
</template>

<style lang="scss" scoped>
.rs-button {
    border-radius: 20px;
    padding: 3px 10px;
    width: fit-content;
    transition: all 0.5s ease;
    cursor: pointer;
}

.rs-button.disabled {
    border: 0.8px solid $bg-disabled;
    background-color: white;
    color: $bg-disabled;
    cursor: not-allowed;
}

.rs-button.primary {
    border: 0.8px solid $bg-primary;
    background-color: $bg-primary;
    color: white;
}

.rs-button.secondary {
    border: 0.8px solid $bg-primary;
    background-color: white;
    color: $bg-primary;
}

.rs-button:hover {
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
}

.rs-button:active {
    opacity: 0.8;
}
</style>