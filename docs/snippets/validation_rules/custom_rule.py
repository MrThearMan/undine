from __future__ import annotations

from typing import TYPE_CHECKING

from graphql import ValidationRule

if TYPE_CHECKING:
    from graphql import NameNode, Node, VisitorAction


class MyValidationRule(ValidationRule):
    def enter_name(
        self,
        node: NameNode,
        key: str | int | None,
        parent: Node | tuple[Node, ...] | None,
        path: list[str | int],
        ancestors: list[Node | tuple[Node, ...]],
    ) -> VisitorAction:
        """
        Called when entering a given node, before visiting its children.

        :param node: The current node being visiting.
        :param key: The index or key to this node from the parent node or array.
        :param parent: the parent immediately above this node, which may be an array.
        :param path: The key path to get to this node from the root node.
        :param ancestors: All nodes and arrays visited before reaching parent of this node.
                          These correspond to array indices in `path`.
        :return: Action to be taken on the node:
                 - self.IDLE: no action
                 - self.SKIP: skip visiting this node
                 - self.BREAK: stop visiting altogether
                 - self.REMOVE: delete this node
                 - any other value: replace this node with the returned value
        """
        return None

    def leave_name(
        self,
        node: NameNode,
        key: str | int | None,
        parent: Node | tuple[Node, ...] | None,
        path: list[str | int],
        ancestors: list[Node | tuple[Node, ...]],
    ) -> VisitorAction:
        """
        Called when leaving a given node, after visiting its children.

        :param node: The current node being visiting.
        :param key: The index or key to this node from the parent node or array.
        :param parent: the parent immediately above this node, which may be an array.
        :param path: The key path to get to this node from the root node.
        :param ancestors: All nodes and arrays visited before reaching parent of this node.
                          These correspond to array indices in `path`.
        :return: Action to be taken on the node:
                 - self.IDLE: no action
                 - self.BREAK: stop visiting altogether
                 - self.REMOVE: delete this node
                 - any other value: replace this node with the returned value
        """
        return None
