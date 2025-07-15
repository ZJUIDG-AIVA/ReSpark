<script setup>
import { onBeforeMount } from 'vue';
import { useCacheStore } from './stores/cache';
import TopBar from './components/topBar/TopBar.vue';
import DataView from './components/view/DataView/DataView.vue';
import DependencyView from './components/view/DependencyView/DependencyView.vue';
import ContentView from './components/view/ContentView/ContentView.vue';
import GenerationView from './components/view/GenerationView/GenerationView.vue';

const cacheStore = useCacheStore();

onBeforeMount(cacheStore.getCacheList);
</script>

<template>
	<div class="page-container">
		<top-bar></top-bar>
		<div class="view-row">
			<data-view></data-view>
			<dependency-view></dependency-view>
			<content-view></content-view>
			<generation-view></generation-view>
		</div>
	</div>
</template>

<style lang="scss" scoped>
.page-container {
	display: flex;
	flex-direction: column;
	height: 100vh;
	max-height: 100vh;
	overflow: hidden;
	width: 100vw;

	.view-row {
		display: flex;
		height: calc(100vh - 37.1px);
		max-height: calc(100vh - 37.1px);
		width: 100vw;
		box-sizing: border-box;
		gap: 0;
	}
}
</style>
