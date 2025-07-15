import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useModeStore = defineStore('mode', () => {
    const mode = ref('analysis');
    const target = ref('objective');

    return {
        mode,
        target
    };
});