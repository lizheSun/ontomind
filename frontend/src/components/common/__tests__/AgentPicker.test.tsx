import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AgentPicker from '../AgentPicker';
import { agentLooperService } from '../../../services/agentLooper.service';
import { resourcesAPI } from '../../../services';

vi.mock('../../../services/agentLooper.service', () => ({
  agentLooperService: { list: vi.fn() },
}));
vi.mock('../../../services', () => ({
  resourcesAPI: { listAgents: vi.fn() },
}));

describe('AgentPicker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(agentLooperService.list).mockResolvedValue([]);
    vi.mocked(resourcesAPI.listAgents).mockResolvedValue([] as any);
  });

  it('renders platform LLM option by default', async () => {
    render(<AgentPicker />);
    await waitFor(() =>
      expect(screen.getByText(/平台 LLM/)).toBeInTheDocument(),
    );
  });

  it('renders agent looper options when data available', async () => {
    vi.mocked(agentLooperService.list).mockResolvedValue([
      {
        id: 1,
        name: 'Test Agent',
        type: 'custom_looper',
        model: 'gpt-4',
        loop_strategy: 'react',
        is_active: true,
        is_published: false,
        description: 'test',
        updated_at: null,
      },
    ]);
    render(<AgentPicker value={1} />);
    await waitFor(() =>
      expect(screen.getByText('Test Agent')).toBeInTheDocument(),
    );
  });

  it('renders without crash when value=null (platform LLM)', async () => {
    const onChange = vi.fn();
    render(<AgentPicker value={null} onChange={onChange} />);
    await waitFor(() =>
      expect(screen.getByText('平台 LLM')).toBeInTheDocument(),
    );
  });
});
