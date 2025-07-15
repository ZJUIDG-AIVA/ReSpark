<script setup>
const props = defineProps(['title', 'indent', 'loading']);
defineEmits(['clickGenerate', 'clickDelete']);
const width = `calc(100% - ${props.indent} * 20px)`;
</script>

<template>
    <div class="header-node">
        <div class="title">{{ props.title }}</div>
        <div class="button-row">
            <div class="flex-grow"></div>
            <img class="button" src="/table_delete_button.svg" @click.stop="$emit('clickDelete')" />
            <img class="button" :class="{ loading: props.loading }" src="/gentitle.svg" @click.stop="$emit('clickGenerate')" />
        </div>
    </div>
</template>

<style lang="scss" scoped>
@keyframes spin {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}

.header-node {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: space-between;
    border-radius: 5px;
    padding: 7px;
    padding-bottom: 10px;
    box-sizing: border-box;
    border: 1px solid #2c3d83;
    background-color: white;
    width: v-bind(width);
    height: 80px;
    
    .title {
        font-size: 13px;
        font-weight: bold;
        text-align: right;
    }

    .button-row {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 5px;

        .button {
            width: 12px;
            height: 12px;
        }

        .button:hover {
            cursor: pointer;
        }

        .button.loading {
            animation: spin 1s infinite linear;
        }
    }
}
</style>