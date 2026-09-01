import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Popconfirm } from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { kanbanService } from '../../services/kanban.service';
import { useKanbanStore } from '../../stores/kanbanStore';

export function BoardRail() {
  const navigate = useNavigate();
  const { boardId } = useParams();
  const boards = useKanbanStore((s) => s.boards);
  const loadBoards = useKanbanStore((s) => s.loadBoards);
  const createBoard = useKanbanStore((s) => s.createBoard);

  useEffect(() => {
    void loadBoards();
  }, [loadBoards]);

  const active = boardId ? Number(boardId) : boards[0]?.id;

  return (
    <div className="om-chat-rail">
      <div className="om-chat-rail-actions">
        <Button
          type="primary"
          icon={<PlusOutlined />}
          block
          onClick={async () => {
            const b = await createBoard('新看板');
            navigate(`/board/${b.id}`);
          }}
        >
          新看板
        </Button>
      </div>
      <div className="om-chat-sess-list">
        {boards.length === 0 ? (
          <div className="om-chat-sess-empty">还没有看板。点上方创建。</div>
        ) : (
          boards.map((b) => {
            const on = b.id === active;
            return (
              <div key={b.id} className={on ? 'om-chat-sess active' : 'om-chat-sess'}>
                <button type="button" className="om-chat-sess-main" onClick={() => navigate(`/board/${b.id}`)}>
                  <span className="om-chat-sess-title">{b.name}</span>
                  <span className="om-chat-sess-meta">
                    {b.columns.length} 列 · {b.task_count} 任务
                  </span>
                </button>
                {boards.length > 1 ? (
                  <Popconfirm
                    title="删除这块看板？"
                    okText="删除"
                    cancelText="取消"
                    onConfirm={async () => {
                      await kanbanService.deleteBoard(b.id);
                      await loadBoards();
                      const next = useKanbanStore.getState().boards[0];
                      navigate(next ? `/board/${next.id}` : '/board');
                    }}
                  >
                    <button type="button" className="om-chat-sess-del" aria-label="删除看板">
                      <DeleteOutlined />
                    </button>
                  </Popconfirm>
                ) : null}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
