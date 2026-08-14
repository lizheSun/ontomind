/** 算力管理 Zustand Store */
import { create } from 'zustand';
import type { AxiosError } from 'axios';
import type {
  ComputeNode,
  ContainerInfo,
  ImageInfo,
  ContainerCreateData,
  ContainerUpdateRequest,
  ContainerExecRequest,
  ContainerExecResponse,
  ContainerExecLogsResponse,
  CommandTemplate,
  ContainerPreset,
  AideContainerSource,
} from '../types/compute';
import * as computeService from '../services/compute.service';

/** 从 Axios 错误中提取后端返回的可读信息 */
export function extractErrMsg(err: unknown): string {
  const e = err as AxiosError<{ message?: string; code?: string }>;
  if (e?.code === 'ECONNABORTED' || /timeout/i.test(e?.message ?? '')) {
    return '请求超时：操作耗时过长（可能在拉取镜像），请稍后刷新查看结果';
  }
  if (e?.response?.data?.message) return e.response.data.message;
  if (e?.message === 'Network Error') {
    return '无法连接后端服务，请确认 uvicorn 已启动（http://localhost:8000）';
  }
  return e?.message || String(err);
}

interface ComputeState {
  // 节点
  nodes: ComputeNode[];
  selectedNode: ComputeNode | null;
  nodesLoading: boolean;

  // Docker
  images: ImageInfo[];
  imagesLoading: boolean;
  containers: ContainerInfo[];
  containersLoading: boolean;
  showAllContainers: boolean;
  /** Docker 拉取失败的原因，供 UI 直接展示（不再静默） */
  dockerError: string | null;

  // 快速命令
  templates: CommandTemplate[];
  templatesLoading: boolean;

  // 容器预设
  presets: ContainerPreset[];
  presetsLoading: boolean;

  // AIDE 源
  aideSources: AideContainerSource[];
  aideSourcesLoading: boolean;

  // 操作
  fetchNodes: () => Promise<void>;
  selectNode: (node: ComputeNode | null) => void;
  createNode: (data: Parameters<typeof computeService.createNode>[0]) => Promise<ComputeNode>;
  updateNode: (id: number, data: Parameters<typeof computeService.updateNode>[1]) => Promise<ComputeNode>;
  deleteNode: (id: number) => Promise<void>;
  testNodeConnection: (id: number) => Promise<void>;
  ensureLocalNode: () => Promise<void>;

  fetchImages: () => Promise<void>;
  fetchContainers: () => Promise<void>;
  pullImage: (image: string) => Promise<void>;
  toggleShowAll: () => void;
  createContainer: (data: ContainerCreateData) => Promise<ContainerInfo>;
  startContainer: (containerId: string) => Promise<void>;
  stopContainer: (containerId: string) => Promise<void>;
  restartContainer: (containerId: string) => Promise<void>;
  removeContainer: (containerId: string, force?: boolean) => Promise<void>;
  updateContainer: (containerId: string, data: ContainerUpdateRequest) => Promise<ContainerInfo>;

  // 快速命令
  fetchTemplates: () => Promise<void>;
  execCommand: (containerId: string, data: ContainerExecRequest) => Promise<ContainerExecResponse>;
  getCommandLogs: (containerId: string, execId: string) => Promise<ContainerExecLogsResponse>;

  // 容器预设
  fetchPresets: () => Promise<void>;

  // AIDE 源
  fetchAideSources: (nodeId?: number) => Promise<void>;
}

const useComputeStore = create<ComputeState>((set, get) => ({
  nodes: [],
  selectedNode: null,
  nodesLoading: false,
  images: [],
  imagesLoading: false,
  containers: [],
  containersLoading: false,
  showAllContainers: true,
  dockerError: null,

  templates: [],
  templatesLoading: false,
  presets: [],
  presetsLoading: false,
  aideSources: [],
  aideSourcesLoading: false,

  // ---- 节点 ----

  ensureLocalNode: async () => {
    try {
      const node = await computeService.getLocalNode();
      const prevSelected = get().selectedNode;
      set((s) => {
        const exists = s.nodes.some((n) => n.id === node.id);
        return {
          nodes: exists
            ? s.nodes.map((n) => (n.id === node.id ? node : n))
            : [...s.nodes, node],
          selectedNode: s.selectedNode ?? node,
        };
      });
      // 首次自动选中本地节点后必须拉取 Docker 数据 ——
      // 旧实现只在 selectNode() 里 fetch，导致进页面时容器/镜像永远是空的
      if (!prevSelected) {
        await Promise.all([get().fetchImages(), get().fetchContainers()]);
      }
    } catch {
      /* 后端不可用，静默 */
    }
  },

  fetchNodes: async () => {
    set({ nodesLoading: true });
    try {
      const nodes = await computeService.listNodes();
      set({ nodes, nodesLoading: false });
    } catch {
      set({ nodesLoading: false });
    }
  },

  selectNode: (node) => {
    set({ selectedNode: node, images: [], containers: [] });
    if (node) {
      useComputeStore.getState().fetchImages();
      useComputeStore.getState().fetchContainers();
    }
  },

  createNode: async (data) => {
    const node = await computeService.createNode(data);
    set((s) => ({ nodes: [...s.nodes, node] }));
    return node;
  },

  updateNode: async (id, data) => {
    const node = await computeService.updateNode(id, data);
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? node : n)),
      selectedNode: s.selectedNode?.id === id ? node : s.selectedNode,
    }));
    return node;
  },

  deleteNode: async (id) => {
    await computeService.deleteNode(id);
    set((s) => ({
      nodes: s.nodes.filter((n) => n.id !== id),
      selectedNode: s.selectedNode?.id === id ? null : s.selectedNode,
    }));
  },

  testNodeConnection: async (id) => {
    await computeService.testNodeConnection(id);
    // 刷新节点列表以更新状态
    const nodes = await computeService.listNodes();
    set((s) => ({
      nodes,
      selectedNode:
        s.selectedNode && nodes.find((n) => n.id === s.selectedNode!.id)
          ? nodes.find((n) => n.id === s.selectedNode!.id)!
          : s.selectedNode,
    }));
  },

  // ---- Docker ----

  fetchImages: async () => {
    const { selectedNode } = get();
    if (!selectedNode) return;
    set({ imagesLoading: true });
    try {
      const images = await computeService.listImages(selectedNode.id);
      set({ images, imagesLoading: false, dockerError: null });
    } catch (err) {
      set({ imagesLoading: false, dockerError: extractErrMsg(err) });
    }
  },

  fetchContainers: async () => {
    const { selectedNode, showAllContainers } = get();
    if (!selectedNode) return;
    set({ containersLoading: true });
    try {
      const containers = await computeService.listContainers(
        selectedNode.id,
        showAllContainers,
      );
      set({ containers, containersLoading: false, dockerError: null });
    } catch (err) {
      // 静默失败是「功能全都不能用但看不到原因」的主因，这里把错误存下来给 UI 展示
      set({ containersLoading: false, dockerError: extractErrMsg(err) });
    }
  },

  toggleShowAll: () => {
    set((s) => ({ showAllContainers: !s.showAllContainers }));
    get().fetchContainers();
  },

  pullImage: async (image) => {
    const { selectedNode } = get();
    if (!selectedNode) throw new Error('未选择节点');
    await computeService.pullImage(selectedNode.id, image);
    await get().fetchImages();
  },

  createContainer: async (data) => {
    const { selectedNode } = get();
    if (!selectedNode) throw new Error('未选择节点');
    const created = await computeService.createContainer(selectedNode.id, data);
    await get().fetchContainers();
    return created;
  },

  startContainer: async (containerId) => {
    const { selectedNode } = get();
    if (!selectedNode) throw new Error('未选择节点');
    await computeService.startContainer(selectedNode.id, containerId);
    await get().fetchContainers();
  },

  stopContainer: async (containerId) => {
    const { selectedNode } = get();
    if (!selectedNode) throw new Error('未选择节点');
    await computeService.stopContainer(selectedNode.id, containerId);
    await get().fetchContainers();
  },

  restartContainer: async (containerId) => {
    const { selectedNode } = get();
    if (!selectedNode) throw new Error('未选择节点');
    await computeService.restartContainer(selectedNode.id, containerId);
    await get().fetchContainers();
  },

  removeContainer: async (containerId, force) => {
    const { selectedNode } = get();
    if (!selectedNode) throw new Error('未选择节点');
    await computeService.removeContainer(selectedNode.id, containerId, force);
    await get().fetchContainers();
  },

  updateContainer: async (containerId, data) => {
    const { selectedNode } = get();
    if (!selectedNode) throw new Error('未选择节点');
    const updated = await computeService.updateContainer(
      selectedNode.id,
      containerId,
      data,
    );
    await get().fetchContainers();
    return updated;
  },

  // ---- 快速命令 ----

  fetchTemplates: async () => {
    set({ templatesLoading: true });
    try {
      const templates = await computeService.listCommandTemplates();
      set({ templates, templatesLoading: false });
    } catch {
      set({ templatesLoading: false });
    }
  },

  execCommand: async (containerId, data) => {
    const { selectedNode } = get();
    if (!selectedNode) throw new Error('未选择节点');
    return computeService.execContainerCommand(selectedNode.id, containerId, data);
  },

  getCommandLogs: async (containerId, execId) => {
    const { selectedNode } = get();
    if (!selectedNode) throw new Error('未选择节点');
    return computeService.getExecLogs(selectedNode.id, containerId, execId);
  },

  // ---- 容器预设 ----

  fetchPresets: async () => {
    if (get().presets.length > 0) return;
    set({ presetsLoading: true });
    try {
      const presets = await computeService.listContainerPresets();
      set({ presets, presetsLoading: false });
    } catch {
      set({ presetsLoading: false });
    }
  },

  // ---- AIDE 源 ----

  fetchAideSources: async (nodeId) => {
    set({ aideSourcesLoading: true });
    try {
      const sources = await computeService.listAideSources(nodeId);
      set({ aideSources: sources, aideSourcesLoading: false });
    } catch {
      set({ aideSourcesLoading: false });
    }
  },
}));

export default useComputeStore;
