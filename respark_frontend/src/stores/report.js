import { defineStore } from 'pinia';
import { useCacheStore } from './cache';
import { ref, computed } from 'vue';
import { useGenerationStore } from './generation';
import { useDataStore } from './data';
import { useLogger } from '@/logger';

const logger = useLogger();

export const useReportStore = defineStore('report', () => {
    const fileName = ref('');
    const nodes = ref([]);
    const nodesForRestore = ref([]);
    const edges = ref([]);
    const edgesForRestore = ref([]);
    const selectedReportId = ref('');
    const indexToGenerate = ref(0);
    const newId = ref('0');

    function restore() {
        nodes.value = nodesForRestore.value;
        edges.value = edgesForRestore.value;
    }

    function uploadReport(formData, cb) {
        const cacheStore = useCacheStore();

        fetch(`http://localhost:5000/split_report?cache_path=${cacheStore.selectedCacheName}&use_cache=${cacheStore.isUseCache}&update_cache=${cacheStore.isUpdateCache}`, {
            method: 'POST',
            body: formData,
        })
            .then(response => response.json())
            .then(() => {
                if (cb)
                    cb();
            })
            .catch(err => {
                console.error(err);
                alert('Failed to upload report');
                if (cb)
                    cb();
            })
    }

    const selectedNodeId = ref('1');

    const nodeDepth = computed(() => {
        if (edges.value.length === 0)
            return {};
        let result = {};
        let children = {};
        for (let edge of edges.value) {
            if (children[edge.fromId] === undefined)
                children[edge.fromId] = [edge.toId];
            else
                children[edge.fromId].push(edge.toId);
            nodes.value.forEach(node => {
                if (node.id === edge.toId)
                    node.parentId = edge.fromId;
            })
        }
        
        function search(node, depth) {
            result[node] = depth;
            if (!children[node])
                return;
            for (let i = 0; i < children[node].length; ++i)
                search(children[node][i], depth + i);
        }

        search('-1', 0);

        return result;
    });

    const numberOfTitlesBeforeNode = computed(() => {
        let result = {};
        for (let i = 0; i < nodes.value.length; ++i)
            if (nodes.value[i].type === 'header')
                for (let j = i + 1; j < nodes.value.length; ++j) 
                    if (result[nodes.value[j].id] === undefined)
                        result[nodes.value[j].id] = 1;
                    else
                        result[nodes.value[j].id]++;
        return result;
    });

    const indents = computed(() => {
        let result = {};
        for (const node of nodes.value.filter(node => node.type === 'header'))
            for (const nodeId of node.childrenNode)
                if (result[nodeId])
                    result[nodeId]++;
                else
                    result[nodeId] = 1;
        return result;
    });

    const position = computed(() => {
        if (edges.value.length === 0)
            return {};
        const result = {}, tree = {};
        for (const edge of edges.value) {
            if (tree[edge.fromId] === undefined)
                tree[edge.fromId] = [edge.toId];
            else
                tree[edge.fromId].push(edge.toId);
        }

        function search(node, currentWidth, left) {
            result[node] = {
                width: currentWidth,
                left: left
            };
            if (!tree[node])
                return;
            for (let i = 0; i < tree[node].length; ++i)
                search(tree[node][i], currentWidth / tree[node].length, left + i * currentWidth / tree[node].length);
        }
        search('-1', 130, 0);

        return result;
    });

    function addParaNode(parentId) {
        let newNode = {
            "id": newId.value,
            "parentId": parentId,
            "level": 1,
            "type": "paragraph",
            "matchType": "Matched",
            "content": [{
                "type": "text",
                "text": ""
            }],
            "analysis": {
                "question": "New objective",
                "operation": "",
                "reason": ""
            }
        };
        let parent = nodes.value.find(node => node.id === parentId);
        let index = nodes.value.indexOf(parent);
        nodes.value.splice(index + 1, 0, newNode);
        nodes.value.filter(node => node.type === 'header').forEach(node => {
            if (node.childrenNode.indexOf(parentId) !== -1)
                node.childrenNode.push(newNode.id);
        });
        logger.log('Added paragraph node with ID ' + newId.value + ', whose parent is ' + parentId);
        newId.value = (parseInt(newId.value) + 1).toString();
    }

    function addHeaderNode(startIndex, endIndex) {
        if (Array.from(new Set(nodes.value.slice(startIndex, endIndex + 1).map(node => indents.value[node.id]))).length > 1) {
            alert('Nodes to be grouped should be in the same level');
            return;
        }
        let newNode = {
            "id": newId.value,
            "parentId": nodes.value[startIndex - 1] ? nodes.value[startIndex - 1].id : '-1',
            "level": 1,
            "type": "header",
            "content": [{
                "type": "text",
                "text": "New Title"
            }],
            "childrenNode": nodes.value.slice(startIndex, endIndex + 1).map(node => node.id)
        };
        let parent = nodes.value.find(node => node.id === (nodes.value[startIndex - 1] ? nodes.value[startIndex - 1].id : '-1'));
        let index = nodes.value.indexOf(parent);
        if (index !== -1)
            nodes.value.splice(index + 1, 0, newNode);
        else
            nodes.value.unshift(newNode);
        for (const headerNode of nodes.value.filter(node => node.type === 'header' && node.id !== newId.value)) {
            for (const nodeId of newNode.childrenNode) 
                if (headerNode.childrenNode.find(id => id === nodeId)) {
                    headerNode.childrenNode.push(newNode.id);
                    break;
                }
        }
        newId.value = (parseInt(newId.value) + 1).toString();
    }

    function deleteParaNode(nodeId) {
        const originalIndex = nodes.value.filter(node => node.type !== 'header').indexOf(nodes.value.find(node => node.id === nodeId));
        if (selectedNodeId.value === nodeId) {
            if (originalIndex === 0)
                selectedNodeId.value = nodes.value.filter(node => node.type !== 'header')[0].id;
            else
                selectedNodeId.value = nodes.value.filter(node => node.type !== 'header')[originalIndex - 1].id;
        }
        edges.value = edges.value.filter(edge => edge.fromId !== nodeId && edge.toId !== nodeId);
        let node = nodes.value.find(node => node.id === nodeId);
        let index = nodes.value.indexOf(node);
        nodes.value.splice(index, 1);
        for (const node of nodes.value.filter(node => node.type === 'header'))
            if (node.childrenNode.indexOf(nodeId) !== -1)
                node.childrenNode.splice(node.childrenNode.indexOf(nodeId), 1);
        while (nodes.value.filter(node => node.type === 'header').map(node => node.childrenNode.length).includes(0))
            nodes.value.splice(nodes.value.findIndex(node => node.type === 'header' && node.childrenNode.length === 0), 1);
        logger.log('Deleted node ' + nodeId);
    }

    function deleteHeaderNode(nodeId) {
        const originalIndex = nodes.value.filter(node => node.type !== 'header').indexOf(nodes.value.find(node => node.id === nodeId));
        if (selectedNodeId.value === nodeId) {
            if (originalIndex === 0)
                selectedNodeId.value = nodes.value.filter(node => node.type !== 'header')[0].id;
            else
                selectedNodeId.value = nodes.value.filter(node => node.type !== 'header')[originalIndex - 1].id;
        }
        edges.value = edges.value.filter(edge => edge.fromId !== nodeId && edge.toId !== nodeId);
        let node = nodes.value.find(node => node.id === nodeId);
        let index = nodes.value.indexOf(node);
        nodes.value.splice(index, 1);
        for (const node of nodes.value.filter(node => node.type === 'header'))
            if (node.childrenNode.indexOf(nodeId) !== -1)
                node.childrenNode.splice(node.childrenNode.indexOf(nodeId), 1);
        while (nodes.value.filter(node => node.type === 'header').map(node => node.childrenNode.length).includes(0))
            nodes.value.splice(nodes.value.findIndex(node => node.type === 'header' && node.childrenNode.length === 0), 1);
    }

    function handleGenerateTitle(nodeId, cb) {
        const cacheStore = useCacheStore();

        fetch('http://localhost:5000/organize_title', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                reference_title: nodes.value.find(node => node.id === nodeId).content[0].text,
                report_segments: nodes.value.find(node => node.id === nodeId).childrenNode.filter(_nodeId => {
                    const node = nodes.value.find(node => node.id === _nodeId);
                    return node && node.type !== 'header';
                }).map(nodeId => {
                    const node = nodes.value.find(node => node.id === nodeId);
                    const fromEdge = edges.value.find(edge => edge.toId === nodeId);
                    return fromEdge ? {
                        question: node.analysis.question,
                        content: node.content.filter(item => item.type === 'text'),
                        logic: fromEdge.relation,
                        'formed from': nodes.value.find(node => node.id === fromEdge.fromId) ? nodes.value.find(node => node.id === fromEdge.fromId).content.filter(item => item.type === 'text') : [],
                    } : {
                        content: node.content.filter(item => item.type === 'text'),
                        logic: '',
                        'formed from': '',
                    };
                }),
                cache_path: cacheStore.selectedCacheName,
                use_cache: cacheStore.isUseCache,
                update_cache: cacheStore.isUpdateCache
            })
        })
            .then(response => {
                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let buffer = '';

                function processStreamResult(result) {
                    const chunk = decoder.decode(result.value, { stream: !result.done });
                    buffer += chunk;
                    const lines = buffer.split('\n');
                    buffer = lines.pop();
                    lines.forEach(line => {
                        if (line.trim().length > 0) {
                            const data = JSON.parse(line.trim().split('data: ')[1]);
                            if (data.stage === 'organize_result')
                                nodes.value.find(node => node.id === nodeId).content[0].text = data.content[0].text;
                        }
                    });
                    if (!result.done)
                        return reader.read().then(processStreamResult);
                    else if (cb)
                        cb();
                }

                return reader.read().then(processStreamResult);
            })
    }

    function resetReport() {
        fileName.value = '';
        nodes.value = [];
        nodesForRestore.value = [];
        edges.value = [];
        edgesForRestore.value = [];
        indexToGenerate.value = 0;
        newId.value = '0';
    }

    function exportReport() {
        const generationStore = useGenerationStore();
        const dataStore = useDataStore();
        const cacheStore = useCacheStore();

        const aElement = document.createElement('a');
        aElement.download = fileName.value + '.json';
        aElement.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(JSON.stringify({
            nodes: nodes.value,
            edges: edges.value,
            generation: {
                objectiveResult: generationStore.objectiveResult,
                contentResult: generationStore.contentResult,
                objectiveCompletedFlags: generationStore.objectiveCompletedFlags,
                contentCompletedFlags: generationStore.contentCompletedFlags,
            },
            data: {
                isDataUploaded: dataStore.isDataUploaded,
                fileName: dataStore.fileName,
                cacheFileName: dataStore.cacheFileName,
                description: dataStore.description,
                fields: dataStore.fields,
                selectedDatasetId: dataStore.selectedDatasetId,
            },
            reportInfo: {
                fileName: fileName.value,
                selectedReportId: selectedReportId.value,
                indexToGenerate: indexToGenerate.value,
                newId: newId.value,
                selectedCacheName: cacheStore.selectedCacheName,
            },
            logs: logger.getLogs(),
        }));
        aElement.click();
        console.log(logger.getLogs());
    }

    function exportHTML() {
        const aElement = document.createElement('a');
        aElement.download = nodes.value.find(node => node.type === 'header').content[0].text + '.html';
        aElement.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(`
            <!DOCTYPE html>
            <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta http-equiv="X-UA-Compatible" content="IE=edge">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>${ nodes.value.find(node => node.type === 'header').content[0].text }</title>
                </head>
                <body>
                    ${ nodes.value.map(node => {
                        if (node.type === 'header') {
                            let level = (indents.value[node.id] || 0) + 1;
                            return `<h${ level }>${ node.content[0].text }</h${ level }>`;
                        } else {
                            let ret = '';
                            for (const item of node.content) {
                                if (item.type === 'text')
                                    ret += `<p>${ item.text }</p>`;
                                else
                                    ret += `<img src="${ item.image_url }">`;
                            }
                            return ret;
                        }
                    }).join('') }
                </body>
            </html>
        `);
        aElement.click();
    }

    return {
        indexToGenerate,
        fileName,
        nodes,
        nodesForRestore,
        edges,
        edgesForRestore,
        selectedReportId,
        numberOfTitlesBeforeNode,
        indents,
        selectedNodeId,
        nodeDepth,
        position,
        newId,
        restore,
        uploadReport,
        addParaNode,
        addHeaderNode,
        deleteParaNode,
        deleteHeaderNode,
        handleGenerateTitle,
        resetReport,
        exportReport,
        exportHTML
    };
});