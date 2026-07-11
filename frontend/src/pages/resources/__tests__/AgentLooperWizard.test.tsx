import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { App as AntApp } from 'antd';
import AgentLooperWizard from '../AgentLooperWizard';
import api from '../../../services/api';

vi.mock('../../../services/api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

beforeAll(() => {
  if (typeof globalThis.ResizeObserver === 'undefined') {
    class RO {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    }
    (globalThis as unknown as { ResizeObserver: typeof RO }).ResizeObserver = RO;
  }
});

function renderWizard(props: Parameters<typeof AgentLooperWizard>[0] = {}) {
  return render(
    <MemoryRouter>
      <AntApp>
        <AgentLooperWizard {...props} />
      </AntApp>
    </MemoryRouter>,
  );
}

describe('AgentLooperWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders 4 steps and 4 preset cards on step 1', () => {
    renderWizard();

    // Step titles rendered by antd Steps
    expect(screen.getByText('定位')).toBeInTheDocument();
    expect(screen.getByText('能力')).toBeInTheDocument();
    expect(screen.getByText('系统提示词')).toBeInTheDocument();
    expect(screen.getByText('联通测试')).toBeInTheDocument();

    // 4 preset cards
    expect(screen.getByTestId('preset-card-general')).toBeInTheDocument();
    expect(screen.getByTestId('preset-card-data_analyst')).toBeInTheDocument();
    expect(screen.getByTestId('preset-card-sql_writer')).toBeInTheDocument();
    expect(screen.getByTestId('preset-card-metadata_reviewer')).toBeInTheDocument();

    // Preset names visible
    expect(screen.getByText('通用助手')).toBeInTheDocument();
    expect(screen.getByText('数据分析师')).toBeInTheDocument();
    expect(screen.getByText('SQL 编写员')).toBeInTheDocument();
    expect(screen.getByText('元数据审核员')).toBeInTheDocument();
  });

  it('applies a preset when its card is clicked (temperature + loop_strategy propagate to step 2)', () => {
    renderWizard();

    // Fill name first so we can proceed
    fireEvent.change(screen.getByTestId('wizard-name'), {
      target: { value: 'my-analyst' },
    });

    // Click SQL 编写员 preset (temperature 0.1, loop_strategy 'react')
    fireEvent.click(screen.getByTestId('preset-card-sql_writer'));

    // Advance to step 2
    fireEvent.click(screen.getByTestId('wizard-next'));

    // model input still empty (preset uses '')
    const modelInput = screen.getByTestId('wizard-model') as HTMLInputElement;
    expect(modelInput.value).toBe('');

    // temperature InputNumber shows 0.1
    const tempInput = screen.getByRole('spinbutton', {
      name: 'temperature',
    }) as HTMLInputElement;
    expect(tempInput.value).toBe('0.1');
  });

  it('calls agentLooperService.create (via api.post) on 完成注册 and passes full config_json', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      data: { code: 0, message: 'ok', data: { id: 42, name: 'my-agent' } },
    });

    const onCreated = vi.fn();
    renderWizard({ onCreated });

    // Step 1: name + description
    fireEvent.change(screen.getByTestId('wizard-name'), {
      target: { value: 'my-agent' },
    });
    fireEvent.change(screen.getByTestId('wizard-description'), {
      target: { value: 'desc' },
    });
    // Apply 通用助手 to fill defaults
    fireEvent.click(screen.getByTestId('preset-card-general'));

    // Step 1 -> 2 -> 3 -> 4
    fireEvent.click(screen.getByTestId('wizard-next'));
    fireEvent.click(screen.getByTestId('wizard-next'));
    fireEvent.click(screen.getByTestId('wizard-next'));

    // Finish
    fireEvent.click(screen.getByTestId('wizard-finish'));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/agent-loopers',
        expect.objectContaining({
          name: 'my-agent',
          type: 'custom_looper',
          description: 'desc',
          config_json: expect.objectContaining({
            loop_strategy: 'single_shot',
            temperature: 0.7,
            system_prompt: expect.stringContaining('通用 AI 助手'),
          }),
        }),
      );
      expect(onCreated).toHaveBeenCalledWith(42);
    });
  });
});
