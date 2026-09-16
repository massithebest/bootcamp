type Node = { type: string; depth?: number; children?: Node[] };

/** Each answer has a level-2 label. Normalize content below it without changing size tokens. */
export function remarkChatHeadings() {
  return (tree: Node) => {
    const stack: number[] = [];
    const visit = (node: Node) => {
      if (node.type === "heading" && node.depth !== undefined) {
        const sourceDepth = node.depth;
        while (stack.length && stack[stack.length - 1] >= sourceDepth) stack.pop();
        node.depth = Math.min(6, 3 + stack.length);
        stack.push(sourceDepth);
      }
      node.children?.forEach(visit);
    };
    visit(tree);
  };
}
