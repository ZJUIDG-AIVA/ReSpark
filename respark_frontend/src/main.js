import './assets/main.css';

import { createApp } from 'vue';
import { createPinia } from 'pinia';
import 'highlight.js/styles/stackoverflow-light.css'
import 'highlight.js/lib/common';
import hljsVuePlugin from "@highlightjs/vue-plugin";
import App from './App.vue';

const pinia = createPinia();
const app = createApp(App);

app.use(pinia);
app.use(hljsVuePlugin);
app.mount('#app');