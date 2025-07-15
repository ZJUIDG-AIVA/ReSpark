import { ref } from 'vue';

const openedDialogs = ref(0);

export function useDialog() {
    function openDialog() {
        openedDialogs.value ++;
    }
    
    function closeDialog() {
        openedDialogs.value --;
    }

    return {
        openedDialogs,
        openDialog,
        closeDialog,
    };
}