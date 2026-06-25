<script lang="ts">
  import { t } from "../../lib/i18n";
  import type { TreeNode } from "../../lib/itemTree";
  import {
    cloneTree,
    findParentFolderId,
    getChildrenAt,
    isDestNode,
    isFolderNode,
    isMarkerNode,
    listValidMoveTargets,
    moveTreeNode,
    parentIdOrEmpty,
  } from "../../lib/itemTree";

  export let tree: TreeNode[];
  export let leafKind: "dest" | "marker";
  export let onTreeChange: (next: TreeNode[]) => void;
  export let onPickFolder: (() => Promise<string | null>) | null = null;

  let currentFolderId: string | null = null;
  let editIdx: number | null = null;
  let editLabel = "";
  let editPath = "";
  let editMode: "leaf" | "folder" = "leaf";
  let moveOpenIdx: number | null = null;
  let dragFrom: { folderId: string | null; index: number } | null = null;
  let dropTargetFolderId: string | null = null;
  let dropInsertIndex: number | null = null;

  $: visible = getChildrenAt(tree, currentFolderId);
  $: parentFolderId = currentFolderId ? findParentFolderId(tree, currentFolderId) : null;

  function emit(next: TreeNode[]) {
    onTreeChange(cloneTree(next));
  }

  function applyMove(fromFolderId: string | null, fromIndex: number, toFolderId: string | null, toIndex?: number) {
    const result = moveTreeNode(tree, fromFolderId, fromIndex, toFolderId, toIndex);
    if (result) emit(result);
  }

  function replaceChildren(nextChildren: TreeNode[]) {
    const next = cloneTree(tree);
    if (!currentFolderId) {
      emit(nextChildren);
      return;
    }
    const folder = findFolderMut(next, currentFolderId);
    if (folder) {
      folder.children = nextChildren;
      emit(next);
    }
  }

  function findFolderMut(nodes: TreeNode[], folderId: string): import("../../lib/itemTree").TreeFolder | null {
    for (const node of nodes) {
      if (isFolderNode(node)) {
        if (node.id === folderId) return node;
        const nested = findFolderMut(node.children, folderId);
        if (nested) return nested;
      }
    }
    return null;
  }

  function openAddFolder() {
    const name = t("treeManager.defaultFolderName");
    replaceChildren([...visible, { kind: "folder" as const, id: crypto.randomUUID().slice(0, 12), label: name, children: [] }]);
  }

  async function openAddLeaf() {
    let path = "";
    if (onPickFolder) {
      const picked = await onPickFolder();
      if (!picked) return;
      path = picked;
    }
    const label =
      path.split(/[/\\]/).filter(Boolean).pop() ??
      (leafKind === "dest" ? t("treeManager.defaultDestName") : t("treeManager.defaultMarkerName"));
    const node =
      leafKind === "dest"
        ? ({ kind: "dest" as const, label, path: path || label })
        : ({ kind: "marker" as const, label, path: path || label });
    replaceChildren([...visible, node]);
  }

  function startEdit(idx: number) {
    moveOpenIdx = null;
    const node = visible[idx];
    if (!node) return;
    editIdx = idx;
    if (isFolderNode(node)) {
      editMode = "folder";
      editLabel = node.label;
      editPath = "";
    } else {
      editMode = "leaf";
      editLabel = node.label;
      editPath = isDestNode(node) || isMarkerNode(node) ? node.path : "";
    }
  }

  function saveEdit() {
    if (editIdx === null) return;
    const next = [...visible];
    const node = next[editIdx];
    if (!node) return;
    const label = editLabel.trim();
    if (isFolderNode(node)) node.label = label || node.label;
    else if (isDestNode(node) || isMarkerNode(node)) {
      node.label = label || node.label;
      node.path = editPath.trim() || node.path;
    }
    replaceChildren(next);
    editIdx = null;
  }

  function removeAt(idx: number) {
    replaceChildren(visible.filter((_, i) => i !== idx));
    if (moveOpenIdx === idx) moveOpenIdx = null;
  }

  function moveItem(idx: number, dir: -1 | 1) {
    applyMove(currentFolderId, idx, currentFolderId, idx + dir);
  }

  function moveToTarget(idx: number, targetFolderId: string | null) {
    applyMove(currentFolderId, idx, targetFolderId);
    moveOpenIdx = null;
  }

  function enterFolder(folderId: string) {
    currentFolderId = folderId;
    moveOpenIdx = null;
    clearDragState();
  }

  function goBack() {
    if (!currentFolderId) return;
    currentFolderId = findParentFolderId(tree, currentFolderId);
    moveOpenIdx = null;
    clearDragState();
  }

  function nodeTitle(node: TreeNode): string {
    if (isFolderNode(node)) return `📁 ${node.label}`;
    if (isDestNode(node) || isMarkerNode(node)) return node.label;
    return "";
  }

  function nodeKey(node: TreeNode, i: number): string {
    if (isFolderNode(node)) return node.id;
    if (isDestNode(node) || isMarkerNode(node)) return node.path;
    return String(i);
  }

  function toggleMoveMenu(idx: number) {
    moveOpenIdx = moveOpenIdx === idx ? null : idx;
  }

  function clearDragState() {
    dragFrom = null;
    dropTargetFolderId = null;
    dropInsertIndex = null;
  }

  function onRowDragStart(e: DragEvent, idx: number) {
    if (editIdx !== null) {
      e.preventDefault();
      return;
    }
    dragFrom = { folderId: currentFolderId, index: idx };
    dropTargetFolderId = null;
    dropInsertIndex = null;
    const dt = e.dataTransfer;
    if (dt) {
      dt.effectAllowed = "move";
      dt.setData(
        "application/x-om-tree-move",
        JSON.stringify({ folderId: parentIdOrEmpty(currentFolderId), index: idx })
      );
    }
  }

  function onRowDragEnd() {
    clearDragState();
  }

  function parseDragPayload(e: DragEvent): { folderId: string | null; index: number } | null {
    const raw = e.dataTransfer?.getData("application/x-om-tree-move") ?? "";
    if (!raw) return dragFrom;
    try {
      const parsed = JSON.parse(raw) as { folderId?: string; index?: number };
      return {
        folderId: parsed.folderId ? String(parsed.folderId) : null,
        index: Number(parsed.index),
      };
    } catch {
      return dragFrom;
    }
  }

  function onFolderDragOver(e: DragEvent, folderId: string) {
    e.preventDefault();
    dropTargetFolderId = folderId;
    dropInsertIndex = null;
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
  }

  function onFolderDrop(e: DragEvent, folderId: string) {
    e.preventDefault();
    e.stopPropagation();
    const from = parseDragPayload(e);
    clearDragState();
    if (!from || !Number.isFinite(from.index)) return;
    applyMove(from.folderId, from.index, folderId);
  }

  function onRowDragOver(e: DragEvent, idx: number) {
    e.preventDefault();
    dropTargetFolderId = null;
    dropInsertIndex = idx;
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
  }

  function onRowDrop(e: DragEvent, idx: number) {
    e.preventDefault();
    e.stopPropagation();
    const from = parseDragPayload(e);
    clearDragState();
    if (!from || !Number.isFinite(from.index)) return;
    applyMove(from.folderId, from.index, currentFolderId, idx);
  }

  function onParentDropZoneOver(e: DragEvent) {
    e.preventDefault();
    dropTargetFolderId = "__parent__";
    dropInsertIndex = null;
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
  }

  function onParentDropZoneDrop(e: DragEvent) {
    e.preventDefault();
    const from = parseDragPayload(e);
    clearDragState();
    if (!from || !Number.isFinite(from.index)) return;
    applyMove(from.folderId, from.index, parentFolderId);
  }

  function onRootDropZoneOver(e: DragEvent) {
    e.preventDefault();
    dropTargetFolderId = "__root__";
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
  }

  function onRootDropZoneDrop(e: DragEvent) {
    e.preventDefault();
    const from = parseDragPayload(e);
    clearDragState();
    if (!from || !Number.isFinite(from.index)) return;
    applyMove(from.folderId, from.index, null);
  }
</script>

<div class="tree-mgr">
  <div class="tree-mgr__toolbar">
    {#if currentFolderId}
      <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={goBack} title={t("treeManager.back")}>←</button>
    {/if}
    <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={openAddFolder}>+ {t("treeManager.addFolder")}</button>
    <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={() => void openAddLeaf()}>+ {leafKind === "dest" ? t("treeManager.addDest") : t("treeManager.addMarker")}</button>
  </div>

  {#if dragFrom}
    {#if currentFolderId}
      <div
        class="tree-mgr__drop-zone"
        class:tree-mgr__drop-zone--active={dropTargetFolderId === "__parent__"}
        role="presentation"
        on:dragover={onParentDropZoneOver}
        on:dragleave={() => (dropTargetFolderId = null)}
        on:drop={onParentDropZoneDrop}
      >
        {t("treeManager.dropToParent")}
      </div>
    {:else}
      <div
        class="tree-mgr__drop-zone"
        class:tree-mgr__drop-zone--active={dropTargetFolderId === "__root__"}
        role="presentation"
        on:dragover={onRootDropZoneOver}
        on:dragleave={() => (dropTargetFolderId = null)}
        on:drop={onRootDropZoneDrop}
      >
        {t("treeManager.dropToRoot")}
      </div>
    {/if}
  {/if}

  <p class="tree-mgr__hint">{t("treeManager.moveHint")}</p>

  {#if visible.length === 0}
    <p class="tree-mgr__empty">{t("treeManager.empty")}</p>
  {:else}
    <ul class="tree-mgr__list">
      {#each visible as node, i (nodeKey(node, i))}
        <li
          class="tree-mgr__row"
          class:tree-mgr__row--drop={dropInsertIndex === i && !isFolderNode(node)}
          class:tree-mgr__row--folder-drop={isFolderNode(node) && dropTargetFolderId === node.id}
          draggable={editIdx !== i}
          on:dragstart={(e) => onRowDragStart(e, i)}
          on:dragend={onRowDragEnd}
          on:dragover={(e) => {
            if (isFolderNode(node)) onFolderDragOver(e, node.id);
            else onRowDragOver(e, i);
          }}
          on:dragleave={() => {
            if (isFolderNode(node) && dropTargetFolderId === node.id) dropTargetFolderId = null;
            if (dropInsertIndex === i) dropInsertIndex = null;
          }}
          on:drop={(e) => {
            if (isFolderNode(node) && dropTargetFolderId === node.id) onFolderDrop(e, node.id);
            else onRowDrop(e, i);
          }}
        >
          {#if editIdx === i}
            <div class="tree-mgr__edit">
              <input class="om-input" type="text" bind:value={editLabel} placeholder={t("destinations.namePlaceholder")} />
              {#if editMode === "leaf"}
                <input class="om-input" type="text" bind:value={editPath} placeholder={t("destinations.pathPlaceholder")} />
              {/if}
              <div class="tree-mgr__edit-actions">
                <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={() => (editIdx = null)}>{t("common.cancel")}</button>
                <button type="button" class="om-btn om-btn--primary om-btn--mini" on:click={saveEdit}>{t("common.save")}</button>
              </div>
            </div>
          {:else}
            <span class="tree-mgr__drag" title={t("treeManager.dragTitle")} aria-hidden="true">⠿</span>
            <span class="tree-mgr__label" title={isDestNode(node) || isMarkerNode(node) ? node.path : node.label}>{nodeTitle(node)}</span>
            <div class="tree-mgr__actions">
              {#if isFolderNode(node)}
                <button
                  type="button"
                  class="om-btn om-btn--ghost om-btn--mini tree-mgr__folder-drop"
                  class:tree-mgr__folder-drop--active={dropTargetFolderId === node.id}
                  title={t("treeManager.dropIntoFolder")}
                  on:dragover={(e) => onFolderDragOver(e, node.id)}
                  on:dragleave={() => (dropTargetFolderId = null)}
                  on:drop={(e) => onFolderDrop(e, node.id)}
                  on:click={() => enterFolder(node.id)}
                >→</button>
              {/if}
              <button type="button" class="om-btn om-btn--ghost om-btn--mini" disabled={i === 0} on:click={() => moveItem(i, -1)}>↑</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--mini" disabled={i >= visible.length - 1} on:click={() => moveItem(i, 1)}>↓</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={() => toggleMoveMenu(i)}>{t("treeManager.moveTo")}</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={() => startEdit(i)}>{t("menus.edit")}</button>
              <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={() => removeAt(i)}>{t("common.delete")}</button>
            </div>
          {/if}
        </li>
        {#if moveOpenIdx === i && editIdx !== i}
          <li class="tree-mgr__move-panel">
            <label class="field-label" for="tree-move-{i}">{t("treeManager.moveTo")}</label>
            <select
              id="tree-move-{i}"
              class="om-input tree-mgr__move-select"
              on:change={(e) => moveToTarget(i, (e.currentTarget as HTMLSelectElement).value || null)}
            >
              <option value="" selected disabled>{t("treeManager.chooseFolder")}</option>
              {#each listValidMoveTargets(tree, node, t("treeManager.root")) as target (target.id ?? "__root__")}
                <option value={target.id ?? ""} disabled={parentIdOrEmpty(currentFolderId) === parentIdOrEmpty(target.id)}>
                  {"\u00a0".repeat(target.depth * 2)}{target.depth > 0 ? "└ " : ""}{target.label}
                </option>
              {/each}
            </select>
          </li>
        {/if}
      {/each}
    </ul>
  {/if}
</div>

<style>
  .tree-mgr {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-2);
  }

  .tree-mgr__toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: var(--om-space-1);
  }

  .tree-mgr__hint {
    margin: 0;
    font-size: 0.72rem;
    color: var(--om-text-muted);
    line-height: 1.35;
  }

  .tree-mgr__drop-zone {
    padding: var(--om-space-2);
    border: 1px dashed color-mix(in oklab, var(--om-border-default) 80%, transparent);
    border-radius: var(--om-radius-sm);
    font-size: 0.72rem;
    color: var(--om-text-muted);
    text-align: center;
  }

  .tree-mgr__drop-zone--active {
    border-color: color-mix(in oklab, var(--om-accent) 70%, white);
    background: color-mix(in oklab, var(--om-accent) 12%, transparent);
    color: var(--om-text-primary);
  }

  .tree-mgr__empty {
    margin: 0;
    font-size: 0.75rem;
    color: var(--om-text-muted);
  }

  .tree-mgr__list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--om-space-1);
  }

  .tree-mgr__row {
    display: flex;
    align-items: center;
    gap: var(--om-space-1);
    padding: var(--om-space-1) var(--om-space-2);
    border-radius: var(--om-radius-sm);
    background: color-mix(in oklab, var(--om-surface-3) 70%, transparent);
    border: 1px solid color-mix(in oklab, var(--om-border-default) 60%, transparent);
    cursor: grab;
  }

  .tree-mgr__row:active {
    cursor: grabbing;
  }

  .tree-mgr__row--drop {
    border-color: color-mix(in oklab, var(--om-accent-2) 65%, white);
    box-shadow: inset 0 2px 0 color-mix(in oklab, var(--om-accent-2) 80%, transparent);
  }

  .tree-mgr__row--folder-drop {
    border-color: color-mix(in oklab, var(--om-accent) 65%, white);
    background: color-mix(in oklab, var(--om-accent) 10%, transparent);
  }

  .tree-mgr__drag {
    flex-shrink: 0;
    opacity: 0.45;
    font-size: 0.85rem;
    line-height: 1;
    user-select: none;
  }

  .tree-mgr__label {
    flex: 1;
    min-width: 0;
    font-size: 0.75rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tree-mgr__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
    flex-shrink: 0;
  }

  .tree-mgr__folder-drop--active {
    border-color: color-mix(in oklab, var(--om-accent) 70%, white);
    background: color-mix(in oklab, var(--om-accent) 14%, transparent);
  }

  .tree-mgr__edit {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-1);
    width: 100%;
  }

  .tree-mgr__edit-actions {
    display: flex;
    gap: var(--om-space-1);
    justify-content: flex-end;
  }

  .tree-mgr__move-panel {
    display: flex;
    flex-direction: column;
    gap: var(--om-space-1);
    padding: var(--om-space-1) var(--om-space-2) var(--om-space-2);
    margin-top: -2px;
    border-radius: var(--om-radius-sm);
    background: color-mix(in oklab, var(--om-surface-2) 90%, transparent);
    border: 1px solid color-mix(in oklab, var(--om-border-default) 55%, transparent);
  }

  .tree-mgr__move-select {
    font-size: 0.75rem;
  }
</style>
