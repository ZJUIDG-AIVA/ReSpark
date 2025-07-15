<script setup>
import { useDatabaseStore } from '@/stores/database';
import { ref, computed } from 'vue';
import RsDialog from '@/components/basic/RsDialog.vue';
import { useLogger } from '@/logger';

const logger = useLogger();

const databaseStore = useDatabaseStore();

const props = defineProps(['columns', 'showViewButton', 'data']);
defineEmits(['select']);

const tableData = computed(() => props.data);

const sortKey = ref('');
const sortState = ref('default');

const selectedRowIndex = ref(null);

const reportContent = ref();
const showPreviewDialog = ref(false);

function sortTable(key) {
	if (!props.columns.find(col => col.name === key && col.sortable))
		return;
	if (sortKey.value === key) {
		if (sortState.value === 'desc') {
			sortState.value = 'default';
			sortKey.value = '';
		} else {
			sortState.value = sortState.value === 'asc' ? 'desc' : 'asc';
		}
	} else {
		sortKey.value = key;
		sortState.value = 'asc';
	}
}

const sortedData = computed(() => {
	if (sortState.value === 'default') return tableData.value;
	return [...tableData.value].sort((a, b) => {
		if (a[sortKey.value] < b[sortKey.value]) return sortState.value === 'asc' ? -1 : 1;
		if (a[sortKey.value] > b[sortKey.value]) return sortState.value === 'asc' ? 1 : -1;
		return 0;
	});
});

const deleteFile = (index) => {
	tableData.value.splice(index, 1);
};

const viewFile = (index) => {
	databaseStore.getReportContent(tableData.value[index].id, (content) => {
		reportContent.value = content;
		showPreviewDialog.value = true;
		logger.log('Preview report: ' + tableData.value[index].id);
	});
};
</script>

<template>
	<rs-dialog :visible="showPreviewDialog" title="Preview" :show-cancel="false" @submit="showPreviewDialog = false">
		<div class="preview">
			<div v-for="(item, index) of reportContent" :key="index">
				<p :class="{
					header: item.type === 'header',
					paragraph: item.type === 'paragraph',
				}" v-if="item.type !== 'image'">
					{{ item.content }}
				</p>
				<img class="image" :src="'data:image/png;base64,' + item.content" v-else />
			</div>
		</div>
	</rs-dialog>
	<div class="table-container">
		<table>
			<thead>
				<tr>
					<th v-for="(column, colIndex) of props.columns" @click="sortTable(column.name)" :key="colIndex">
						{{ column.label }}
						<img class="button" src="/sort_updown.svg"
							v-if="column.sortable && sortKey === column.name && sortState === 'asc'">
						<img class="button" src="/sort_downup.svg"
							v-else-if="column.sortable && sortKey === column.name && sortState === 'desc'">
						<img class="button" src="/sort.svg" v-else-if="column.sortable && sortState === 'default'" />
					</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(file, index) in sortedData" :key="index"
					:class="{ gray: index % 2, selected: selectedRowIndex === index }"
					@click="() => { selectedRowIndex = index; $emit('select', index); }">
					<td v-for="(column, colIndex) of props.columns" :key="colIndex">
						<div :title="column.showTooltip ? file[column.name] : ''">{{ file[column.name] }}</div>
					</td>
					<td class="button-row">
						<img class="button" src="/table_show_button.svg" v-if="props.showViewButton"
							@click="viewFile(index)" />
						<img class="button" src="/table_delete_button.svg" @click="deleteFile(index)" />
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<style lang="scss" scoped>
.preview {
	max-height: 50vh;
	overflow: auto;
	display: flex;
	flex-direction: column;
	gap: 10px;

	.header {
		font-size: 18px;
		font-weight: 700;
	}

	.paragraph {
		white-space: pre-wrap;
	}

	.image {
		color: red;
		max-width: 100%;
	}
}

.table-container {
	height: 200px;
	overflow: auto;

	table {
		width: 100%;
		max-height: 600px;
		overflow-y: auto;
		border-collapse: collapse;
		font-size: 12px;

		th,
		td {
			border: 1px solid #ddd;
			padding: 8px;
		}

		td div {
			display: -webkit-box;
			-webkit-box-orient: vertical;
			-webkit-line-clamp: 2;
			line-clamp: 2;
			overflow: hidden;
		}

		td.button-row {
			text-wrap: nowrap;
		}

		th {
			font-weight: 700;
			font-size: 13px;
			color: #384A8C;
			background: rgba(56, 74, 140, 0.05);
			text-wrap: nowrap;
		}

		tr.gray {
			background: rgba(56, 74, 140, 0.05);
		}

		tr.selected td {
			background-color: #384A8C;
			color: white;
		}

		tr.selected td:last-child {
			background-color: unset;
		}

		.button {
			cursor: pointer;
			width: 13px;
			height: 13px;
			margin-right: 5px;
		}
	}
}

::-webkit-scrollbar {
	width: 5px;
}

::-webkit-scrollbar-track {
	background: rgb(179, 177, 177);
	border-radius: 10px;
}

::-webkit-scrollbar-thumb {
	background: rgb(136, 136, 136);
	border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
	background: rgb(100, 100, 100);
	border-radius: 10px;
}

::-webkit-scrollbar-thumb:active {
	background: rgb(68, 68, 68);
	border-radius: 10px;
}
</style>