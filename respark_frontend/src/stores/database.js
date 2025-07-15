import { defineStore } from 'pinia';
import { ref } from 'vue';
import { convertSize } from '@/utils';

export const useDatabaseStore = defineStore('database', () => {
    const datasets = ref([]);
    const reports = ref([]);

    function updateDatabase(cb) {
        fetch('http://localhost:5000/get_database')
            .then(response => response.json())
            .then(data => {
                datasets.value = data.datasets.map(item => {
                    return {
                        id: item.id,
                        name: item.name,
                        size: convertSize(item.size),
                        information: item.information
                    };
                });
                reports.value = data.reports.map(item => {
                    return {
                        id: item.id,
                        name: item.name,
                        size: convertSize(item.size),
                        rawSize: item.size,
                        topic: item.topic,
                        predictedFields: item.predicted_fields.join(', '),
                    };
                });
                if (cb)
                    cb();
            })
            .catch(err => {
                alert('Failed to get database');
                console.error(err);
                if (cb)
                    cb();
            });
    }

    function getReportContent(id, cb) {
        fetch(`http://localhost:5000/get_report_content`, {
            method: 'POST',
            body: JSON.stringify({
                selected_report_id: id
            }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                cb(data);
            })
            .catch(err => {
                alert('Failed to get report content');
                console.error(err);
            });
    }

    return {
        datasets,
        reports,
        updateDatabase,
        getReportContent
    }
});