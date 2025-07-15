import { defineStore } from 'pinia';
import { ref } from 'vue';
import { useReportStore } from './report';
import { useCacheStore } from './cache';
import { useLogger } from '@/logger';

const logger = useLogger();

export const useGenerationStore = defineStore('generation', () => {
    const objectiveResult = ref({});
    const contentResult = ref({});
    const objectiveCompletedFlags = ref([]);
    const contentCompletedFlags = ref([]);

    function doObjectiveGenerate(nodeId, selectedFields, selectedLogic, selectedParentId, cb) {
        const reportStore = useReportStore();
        const cacheStore = useCacheStore();

        const currentNode = reportStore.nodes.find(node => node.id === nodeId);
        const fromEdges = reportStore.edges.filter(edge => edge.toId === nodeId);

        objectiveResult.value[nodeId] = [];
        objectiveCompletedFlags.value = objectiveCompletedFlags.value.filter(flag => flag !== nodeId);

        if (reportStore.nodesForRestore.find(node => node.id === nodeId)) {
            objectiveResult.value[nodeId] = [{ stage: 'step 1', content: [] }];
            fetch('http://localhost:5000/adapt_goal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question: currentNode.analysis.question,
                    content: JSON.stringify(currentNode.content),
                    relation: fromEdges.map(fromEdge => {
                        const fromNode = reportStore.nodes.find(node => node.id === fromEdge.fromId);
                        const originFromNode = reportStore.nodesForRestore.find(node => node.id === fromEdge.fromId);
                        return {
                            edge: fromEdge,
                            fromNode: !fromNode ? 'data' : {
                                original: {
                                    question: originFromNode.analysis.question,
                                    content: originFromNode.content,
                                },
                                new: {
                                    question: fromNode.analysis.question,
                                    content: fromNode.content,
                                },
                            }
                        }
                    }),
                    cache_path: cacheStore.selectedCacheName,
                    use_cache: cacheStore.isUseCache,
                    update_cache: cacheStore.isUpdateCache,
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
                                if (objectiveResult.value[nodeId].find(item => item.stage === data.stage))
                                    objectiveResult.value[nodeId].find(item => item.stage === data.stage).content.push(data.content[0]);
                                else
                                    objectiveResult.value[nodeId].push(data);
                                const stages = ['step 1', 'step 2', 'step 3', 'Final Result'];
                                if (data.content[0].type === 'objective' && data.stage !== 'Final Result')
                                    objectiveResult.value[nodeId].push({ stage: stages[stages.indexOf(data.stage) + 1], content: [] });
                            }
                        });
                        if (!result.done)
                            return reader.read().then(processStreamResult);
                        else {
                            objectiveCompletedFlags.value.push(nodeId);
                            logger.log('Objective generated for node ' + nodeId);
                        }
                    }
    
                    return reader.read().then(processStreamResult);
                })
                .catch(error => {
                    console.error('Error:', error);
                });
        } else {
            fetch('http://localhost:5000/insert_goal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    select_fields: selectedFields,
                    select_logic: [selectedLogic],
                    previous_result: selectedParentId === '-1' ? '' : {
                        question: reportStore.nodes.find(node => node.id === selectedParentId).analysis.question,
                        content: reportStore.nodes.find(node => node.id === selectedParentId).content,
                    },
                    cache_path: cacheStore.selectedCacheName,
                    use_cache: cacheStore.isUseCache,
                    update_cache: cacheStore.isUpdateCache,
                })
            })
                .then(response => response.json())
                .then(data => {
                    reportStore.nodesForRestore.push({
                        ...currentNode,
                        analysis: {
                            question: data.question,
                            reason: data.consideration
                        }
                    });
                    const newEdge = {
                        fromId: selectedParentId + '',
                        toId: nodeId,
                        relation: data.logic,
                        description: data.consideration,
                    };
                    reportStore.edges.push(newEdge);
                    reportStore.edgesForRestore.push(newEdge);
                    currentNode.analysis.question = data.question;
                    objectiveCompletedFlags.value.push(nodeId);
                    logger.log('Objective generated for customized node ' + nodeId + ', with logic ' + selectedLogic + ', from parent node ' + selectedParentId + ', with fields ' + selectedFields);
                    if (cb)
                        cb();
                })
                .catch(err => {
                    console.error(err);
                });
        }
    }

    function doContentGenerate(nodeId) {
        const reportStore = useReportStore();
        const cacheStore = useCacheStore();

        const currentNode = reportStore.nodes.find(node => node.id === nodeId);
        const fromEdges = reportStore.edges.filter(edge => edge.toId === nodeId);

        contentResult.value[nodeId] = [];
        contentCompletedFlags.value = contentCompletedFlags.value.filter(flag => flag !== nodeId);

        if (currentNode.analysis.question) {
            contentResult.value[nodeId] = [{ stage: 'code', content: [{ type: 'code', code: '' }] }];
            fetch('http://localhost:5000/execute_goal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question: currentNode.analysis.question,
                    content: JSON.stringify(currentNode.content),
                    relation: fromEdges.map(fromEdge => {
                        const fromNode = reportStore.nodes.find(node => node.id === fromEdge.fromId);
                        return {
                            edge: fromEdge,
                            fromNode: !fromNode ? 'data' : {
                                question: fromNode.analysis.question,
                                content: fromNode.content,
                            }
                        }
                    }),
                    data_sentences: currentNode.dataSentences || [],
                    non_data_sentences: currentNode.nonDataSentences || [],
                    cache_path: cacheStore.selectedCacheName,
                    use_cache: cacheStore.isUseCache,
                    update_cache: cacheStore.isUpdateCache,
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
                                if (contentResult.value[nodeId].find(item => item.stage === data.stage))
                                    contentResult.value[nodeId].find(item => item.stage === data.stage).content.push(data.content[0]);
                                else
                                    contentResult.value[nodeId].push(data);
                            }
                        });
                        if (!result.done)
                            return reader.read().then(processStreamResult);
                        else {
                            contentCompletedFlags.value.push(nodeId);
                            reportStore.nodes[reportStore.selectedNodeId].highlights = contentResult.value[nodeId].find(item => item.stage === 'non_data_sentences').content;
                            reportStore.nodes[reportStore.selectedNodeId].nonDataSentences = reportStore.nodes[reportStore.selectedNodeId].highlights;
                            logger.log('Report content generated for node ' + nodeId);
                        }
                    }
    
                    return reader.read().then(processStreamResult);
                })
                .catch(error => {
                    console.error('Error:', error);
                });
        } else
            fetch('http://localhost:5000/imitate_text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    report_content: {
                        id: currentNode.id,
                        match_type: currentNode.matchType,
                        text: [currentNode.content[0].text],
                        summary: currentNode.summary
                    },
                    cache_path: cacheStore.selectedCacheName,
                    use_cache: cacheStore.isUseCache,
                    update_cache: cacheStore.isUpdateCache,
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
                                if (contentResult.value[nodeId].find(item => item.stage === data.stage))
                                    contentResult.value[nodeId].find(item => item.stage === data.stage).content.push(data.content[0]);
                                else
                                    contentResult.value[nodeId].push(data);
                            }
                        });
                        if (!result.done)
                            return reader.read().then(processStreamResult);
                        else {
                            contentCompletedFlags.value.push(nodeId);
                            logger.log('Report content generated for node ' + nodeId);
                        }
                    }
    
                    return reader.read().then(processStreamResult);
                })
    }

    return {
        objectiveResult,
        contentResult,
        objectiveCompletedFlags,
        contentCompletedFlags,
        doObjectiveGenerate,
        doContentGenerate,
    };
});