import grimp


def export_mermaid_graph(top_level_module: str) -> None:
    """Builds a flowchart of the module dependencies and exports it to a markdown file."""
    graph = grimp.build_graph(top_level_module)

    flowchart = "```mermaid\nflowchart LR"
    for module in graph.modules:
        for imported in graph.find_modules_directly_imported_by(module):
            flowchart += f"\n    {imported} --> {module}"

    flowchart += "\n```"
    with open(f"{top_level_module}_graph.md", mode="w") as f:  # noqa: PTH123
        f.write(flowchart)


if __name__ == "__main__":
    export_mermaid_graph("undine")
