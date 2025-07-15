const logs = [];

export const useLogger = () => {
    const log = (message) => {
        console.log(message);
        logs.push(message);
    };

    const getLogs = () => logs;

    return {
        log,
        getLogs
    }
};