<script setup>
import { computed, watch } from 'vue';
import RsButton from '@/components/basic/RsButton.vue';
import { useDialog } from './dialog';

const props = defineProps(['visible', 'title', 'pending', 'showSubmit', 'showCancel']);
defineEmits(['close', 'submit']);

const dialogStatus = useDialog();

const modalZIndex = computed(() => dialogStatus.openedDialogs.value * 1100 + 1000);
const dialogZIndex = computed(() => dialogStatus.openedDialogs.value * 1100 + 2000);

watch(() => props.visible, (newValue) => {
    if (newValue)
        dialogStatus.openDialog();
    else
        dialogStatus.closeDialog();
});
</script>

<template>
    <div class="modal" v-if="props.visible">
        <div class="dialog-body" v-if="props.visible" @click.stop>
            <div class="title">{{ props.title }}</div>
            <slot></slot>
            <div class="button-row">
                <rs-button type="secondary" :disabled="props.pending" v-if="props.showCancel || props.showCancel === undefined" @click="$emit('close')">&nbsp;Cancel&nbsp;</rs-button>
                <rs-button type="primary" :disabled="props.pending" v-if="props.showSubmit || props.showSubmit === undefined" @click="$emit('submit')">&nbsp;&nbsp;&nbsp;OK&nbsp;&nbsp;&nbsp;</rs-button>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: v-bind(modalZIndex);
}

.dialog-body {
    position: fixed;
    max-width: 800px;
    background: #FFFFFF;
    box-shadow: 0px 0px 4px rgba(0, 0, 0, 0.25);
    border-radius: 5px;
    z-index: v-bind(dialogZIndex);
    display: flex;
    flex-direction: column;
    padding: 10px 20px;
    gap: 15px;

    .title {
        font-size: 25px;
        line-height: 29px;
        color: #384A8C;
    }

    .button-row {
        display: flex;
        flex-direction: row;
        justify-content: flex-end;
        gap: 10px;
    }
}
</style>