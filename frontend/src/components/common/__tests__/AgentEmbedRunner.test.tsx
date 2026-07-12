import { render, screen, act, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AgentEmbedRunner from '../AgentEmbedRunner';

/**
 * Dispatch an inbound message from the "iframe" back to the parent window.
 * jsdom does not run cross-frame postMessage, so we synthesize MessageEvent
 * with `source` bound to the iframe.contentWindow.
 */
function postFromIframe(iframe: HTMLIFrameElement, data: unknown) {
  const event = new MessageEvent('message', {
    data,
    source: iframe.contentWindow as MessageEventSource,
  });
  window.dispatchEvent(event);
}

describe('AgentEmbedRunner', () => {
  it('renders iframe with src derived from agentId', () => {
    render(<AgentEmbedRunner agentId="aibi" />);
    const iframe = screen.getByTestId('agent-embed-iframe') as HTMLIFrameElement;
    expect(iframe.getAttribute('src')).toBe('/agent-embed/aibi');
    expect(iframe.getAttribute('data-agent-id')).toBe('aibi');
  });

  it('handshake: fires onReady + posts init after ready message', async () => {
    const onReady = vi.fn();
    render(<AgentEmbedRunner agentId={42} context={{ foo: 'bar' }} onReady={onReady} />);
    const iframe = screen.getByTestId('agent-embed-iframe') as HTMLIFrameElement;

    const postSpy = vi.fn();
    // Override contentWindow.postMessage to observe outbound init
    Object.defineProperty(iframe, 'contentWindow', {
      configurable: true,
      value: { postMessage: postSpy },
    });

    act(() => {
      postFromIframe(iframe, { type: 'agent.embed.ready' });
    });

    await waitFor(() => expect(onReady).toHaveBeenCalledTimes(1));
    // Effect posts init after ready flips
    await waitFor(() =>
      expect(postSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'agent.embed.init',
          agentId: 42,
          context: { foo: 'bar' },
        }),
        '*',
      ),
    );
  });

  it('routes result + error inbound messages to callbacks', async () => {
    const onResult = vi.fn();
    const onError = vi.fn();
    render(
      <AgentEmbedRunner
        agentId="aibi"
        onResult={onResult}
        onError={onError}
      />,
    );
    const iframe = screen.getByTestId('agent-embed-iframe') as HTMLIFrameElement;

    act(() => {
      postFromIframe(iframe, {
        type: 'agent.embed.result',
        requestId: 'r1',
        data: { rows: 3 },
      });
      postFromIframe(iframe, {
        type: 'agent.embed.error',
        message: 'boom',
      });
      // Non-protocol message should be ignored
      postFromIframe(iframe, { type: 'unrelated', data: 1 });
    });

    await waitFor(() => {
      expect(onResult).toHaveBeenCalledWith({ rows: 3 }, 'r1');
      expect(onError).toHaveBeenCalledWith('boom');
    });

    expect(screen.getByTestId('agent-embed-error').textContent).toContain('boom');
  });

  it('reload button resets ready state and remounts iframe', async () => {
    render(<AgentEmbedRunner agentId="aibi" />);
    const iframe = screen.getByTestId('agent-embed-iframe') as HTMLIFrameElement;

    act(() => {
      postFromIframe(iframe, { type: 'agent.embed.ready' });
    });
    await waitFor(() => expect(screen.getByText('ready')).toBeInTheDocument());

    const reloadBtn = screen.getByLabelText('reload-agent-embed');
    fireEvent.click(reloadBtn);

    await waitFor(() => expect(screen.getByText('loading')).toBeInTheDocument());
  });
});
