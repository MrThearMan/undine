
const root = ReactDOM.createRoot(document.getElementById('graphiql'));

const headers = {}

const csrftoken = document.querySelector("[name=csrfmiddlewaretoken]").value;

if (csrftoken) {
    headers['X-CSRFToken'] = csrftoken
}

const fetcher = GraphiQL.createFetcher({
    url: '#',
    headers: headers,
});

const explorerPlugin = GraphiQLPluginExplorer.explorerPlugin();

root.render(
    React.createElement(GraphiQL, {
        fetcher,
        defaultEditorToolsVisibility: true,
        plugins: [explorerPlugin],
    })
);
