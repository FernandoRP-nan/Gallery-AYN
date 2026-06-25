/** Tipos y utilidades compartidas para árboles de destinos y marcadores. */

export type TreeFolder = {
  kind: "folder";
  id: string;
  label: string;
  children: TreeNode[];
};

export type TreeDest = {
  kind: "dest";
  label: string;
  path: string;
};

export type TreeMarker = {
  kind: "marker";
  label: string;
  path: string;
};

export type TreeNode = TreeFolder | TreeDest | TreeMarker;

export type DestToolbarItem =
  | { kind: "folder"; id: string; label: string }
  | { kind: "dest"; label: string; path: string; index: number };

export function isFolderNode(node: TreeNode): node is TreeFolder {
  return node.kind === "folder";
}

export function isDestNode(node: TreeNode): node is TreeDest {
  return node.kind === "dest";
}

export function isMarkerNode(node: TreeNode): node is TreeMarker {
  return node.kind === "marker";
}

export function normalizeTreeNodes(raw: unknown, leafKind: "dest" | "marker"): TreeNode[] {
  if (!Array.isArray(raw)) return [];
  const out: TreeNode[] = [];
  for (const x of raw) {
    if (!x || typeof x !== "object") continue;
    const o = x as Record<string, unknown>;
    const kind = String(o.kind ?? "").trim();
    if (kind === "folder") {
      const id = String(o.id ?? "").trim() || crypto.randomUUID().slice(0, 12);
      const label = String(o.label ?? "").trim() || "Carpeta";
      const children = normalizeTreeNodes(o.children, leafKind);
      out.push({ kind: "folder", id, label, children });
      continue;
    }
    if (leafKind === "dest" && (kind === "dest" || o.path || o.folder || o.dir)) {
      const path = String(o.path ?? o.folder ?? o.dir ?? "").trim();
      if (!path) continue;
      const label = String(o.label ?? "").trim() || path;
      out.push({ kind: "dest", label, path });
      continue;
    }
    if (leafKind === "marker" && (kind === "marker" || o.path)) {
      const path = String(o.path ?? "").trim();
      if (!path) continue;
      const label = String(o.label ?? "").trim() || path;
      out.push({ kind: "marker", label, path });
    }
  }
  return out;
}

export function findFolder(nodes: TreeNode[], folderId: string): TreeFolder | null {
  const fid = String(folderId ?? "").trim();
  if (!fid) return null;
  for (const node of nodes) {
    if (!isFolderNode(node)) continue;
    if (node.id === fid) return node;
    const nested = findFolder(node.children, fid);
    if (nested) return nested;
  }
  return null;
}

export function getChildrenAt(nodes: TreeNode[], folderId: string | null): TreeNode[] {
  const fid = String(folderId ?? "").trim();
  if (!fid) return nodes;
  return findFolder(nodes, fid)?.children ?? [];
}

export function flattenMarkerPaths(nodes: TreeNode[]): string[] {
  const paths: string[] = [];
  const walk = (list: TreeNode[]) => {
    for (const node of list) {
      if (isMarkerNode(node)) {
        if (!paths.includes(node.path)) paths.push(node.path);
      } else if (isFolderNode(node)) {
        walk(node.children);
      }
    }
  };
  walk(nodes);
  return paths;
}

export function destToolbarItems(nodes: TreeNode[], folderId: string | null): DestToolbarItem[] {
  const children = getChildrenAt(nodes, folderId);
  const out: DestToolbarItem[] = [];
  children.forEach((node, index) => {
    if (isFolderNode(node)) {
      out.push({ kind: "folder", id: node.id, label: node.label });
    } else if (isDestNode(node)) {
      out.push({ kind: "dest", label: node.label, path: node.path, index });
    }
  });
  return out;
}

export function markerToolbarItems(
  nodes: TreeNode[],
  folderId: string | null
): Array<{ kind: "folder"; id: string; label: string } | { kind: "marker"; label: string; path: string; index: number }> {
  const children = getChildrenAt(nodes, folderId);
  const out: Array<
    { kind: "folder"; id: string; label: string } | { kind: "marker"; label: string; path: string; index: number }
  > = [];
  children.forEach((node, index) => {
    if (isFolderNode(node)) {
      out.push({ kind: "folder", id: node.id, label: node.label });
    } else if (isMarkerNode(node)) {
      out.push({ kind: "marker", label: node.label, path: node.path, index });
    }
  });
  return out;
}

export function folderLabelAt(nodes: TreeNode[], folderId: string | null): string | null {
  if (!folderId) return null;
  return findFolder(nodes, folderId)?.label ?? null;
}

export function cloneTree(nodes: TreeNode[]): TreeNode[] {
  return JSON.parse(JSON.stringify(nodes)) as TreeNode[];
}

export function findParentFolderId(nodes: TreeNode[], folderId: string, parent: string | null = null): string | null {
  const fid = String(folderId ?? "").trim();
  if (!fid) return null;
  for (const node of nodes) {
    if (!isFolderNode(node)) continue;
    if (node.id === fid) return parent;
    const nested = findParentFolderId(node.children, fid, node.id);
    if (nested !== null) return nested;
  }
  return null;
}

export function flattenDestList(nodes: TreeNode[]): Array<{ label: string; path: string }> {
  const out: Array<{ label: string; path: string }> = [];
  const walk = (list: TreeNode[]) => {
    for (const node of list) {
      if (isDestNode(node)) out.push({ label: node.label, path: node.path });
      else if (isFolderNode(node)) walk(node.children);
    }
  };
  walk(nodes);
  return out;
}

export function parentIdOrEmpty(folderId: string | null): string {
  return String(folderId ?? "").trim();
}

/** Referencia mutable a la lista hija de un contenedor. */
function getChildrenRef(nodes: TreeNode[], folderId: string | null): TreeNode[] | null {
  const fid = parentIdOrEmpty(folderId);
  if (!fid) return nodes;
  return findFolder(nodes, fid)?.children ?? null;
}

/** True si targetFolderId está dentro del subárbol de ancestorFolderId. */
export function folderContainsFolder(
  nodes: TreeNode[],
  ancestorFolderId: string,
  targetFolderId: string
): boolean {
  const ancestor = findFolder(nodes, ancestorFolderId);
  if (!ancestor) return false;
  const walk = (list: TreeNode[]): boolean => {
    for (const node of list) {
      if (!isFolderNode(node)) continue;
      if (node.id === targetFolderId) return true;
      if (walk(node.children)) return true;
    }
    return false;
  };
  return walk(ancestor.children);
}

export function canMoveNodeToFolder(
  tree: TreeNode[],
  node: TreeNode,
  targetFolderId: string | null
): boolean {
  if (!isFolderNode(node)) return true;
  const target = parentIdOrEmpty(targetFolderId);
  if (!target) return true;
  if (node.id === target) return false;
  return !folderContainsFolder(tree, node.id, target);
}

/** Mueve un nodo entre contenedores o reordena dentro del mismo. */
export function moveTreeNode(
  tree: TreeNode[],
  fromFolderId: string | null,
  fromIndex: number,
  toFolderId: string | null,
  toIndex?: number
): TreeNode[] | null {
  const next = cloneTree(tree);
  const src = getChildrenRef(next, fromFolderId);
  if (!src || fromIndex < 0 || fromIndex >= src.length) return null;

  const [node] = src.splice(fromIndex, 1);
  if (!node || !canMoveNodeToFolder(next, node, toFolderId)) return null;

  const dst = getChildrenRef(next, toFolderId);
  if (!dst) return null;

  let insertAt = toIndex ?? dst.length;
  const sameParent = parentIdOrEmpty(fromFolderId) === parentIdOrEmpty(toFolderId);
  if (sameParent && fromIndex < insertAt) insertAt -= 1;
  insertAt = Math.max(0, Math.min(insertAt, dst.length));
  dst.splice(insertAt, 0, node);
  return next;
}

export type FolderMoveTarget = { id: string | null; label: string; depth: number };

/** Carpetas válidas como destino al mover un nodo (incluye raíz). */
export function listValidMoveTargets(tree: TreeNode[], node: TreeNode, rootLabel: string): FolderMoveTarget[] {
  const out: FolderMoveTarget[] = [{ id: null, label: rootLabel, depth: 0 }];
  const walk = (nodes: TreeNode[], depth: number) => {
    for (const entry of nodes) {
      if (!isFolderNode(entry)) continue;
      if (isFolderNode(node) && (entry.id === node.id || folderContainsFolder(tree, node.id, entry.id))) continue;
      out.push({ id: entry.id, label: entry.label, depth });
      walk(entry.children, depth + 1);
    }
  };
  walk(tree, 0);
  return out;
}
