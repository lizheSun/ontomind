import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import SmartAddModal from '../components/SmartAddModal';
import { dataPlatformService } from '../../../services/dataPlatform.service';

vi.mock('../../../services/dataPlatform.service', () => ({
  dataPlatformService: {
    parseConfig: vi.fn(),
  },
}));

beforeAll(() => {
  if (!('ResizeObserver' in globalThis)) {
    class ResizeObserverStub {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    }
    (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
      ResizeObserverStub;
  }
});

describe('SmartAddModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls parseConfig on submit and forwards result via onParsed', async () => {
    const mockResult = {
      parsed: {
        name: 'test',
        source_type: 'mysql',
        dialect: 'mysql' as const,
        host: 'h',
        port: 3306,
        username: 'u',
        password: '',
        database: 'd',
        charset: 'utf8mb4',
        default_schema: null,
        description: null,
        read_only_flag: true,
      },
      model_used: 'test-model',
      warnings: [],
    };
    vi.mocked(dataPlatformService.parseConfig).mockResolvedValue(mockResult);

    const onParsed = vi.fn();
    render(<SmartAddModal open onCancel={() => {}} onParsed={onParsed} />);

    const textarea = screen.getByTestId('smart-add-textarea');
    fireEvent.change(textarea, {
      target: { value: 'MYSQL_HOST=h MYSQL_PORT=3306' },
    });

    const submitBtn = screen.getByRole('button', { name: /解\s*析/ });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(dataPlatformService.parseConfig).toHaveBeenCalledWith(
        'MYSQL_HOST=h MYSQL_PORT=3306',
      );
      expect(onParsed).toHaveBeenCalledWith(mockResult);
    });
  });

  it('does not call onParsed when parseConfig rejects', async () => {
    vi.mocked(dataPlatformService.parseConfig).mockRejectedValue({
      response: { data: { message: 'LLM 输出无法解析' } },
    });

    const onParsed = vi.fn();
    render(<SmartAddModal open onCancel={() => {}} onParsed={onParsed} />);

    fireEvent.change(screen.getByTestId('smart-add-textarea'), {
      target: { value: 'garbage' },
    });
    fireEvent.click(screen.getByRole('button', { name: /解\s*析/ }));

    await waitFor(() => {
      expect(dataPlatformService.parseConfig).toHaveBeenCalled();
    });
    expect(onParsed).not.toHaveBeenCalled();
  });

  it('renders the password-safety warning banner', () => {
    render(<SmartAddModal open onCancel={() => {}} onParsed={vi.fn()} />);
    expect(
      screen.getByText(/密码字段将自动留空/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/AI 不会从粘贴的文本中提取密码/),
    ).toBeInTheDocument();
  });
});
