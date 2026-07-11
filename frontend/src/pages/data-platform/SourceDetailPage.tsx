import { useEffect, useState } from 'react';
import { Breadcrumb, Col, Row, Skeleton, Tabs, message } from 'antd';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { PageHeader } from '../../components/common';
import { useDataPlatformStore } from '../../stores/dataPlatformStore';
import { dataPlatformService } from '../../services/dataPlatform.service';
import type { DpDataSource, DpExecuteResponse } from '../../types/dataPlatform';
import SchemaSidebar from './components/SchemaSidebar';
import EditorTab from './tabs/EditorTab';
import ChatTab from './tabs/ChatTab';
import HistoryTab from './tabs/HistoryTab';
import SavedQueriesTab from './tabs/SavedQueriesTab';

type TabKey = 'editor' | 'chat' | 'history' | 'saved';

export default function SourceDetailPage() {
  const { sid } = useParams<{ sid: string }>();
  const sourceId = Number(sid);
  const navigate = useNavigate();

  const schemaCache = useDataPlatformStore((s) => s.schemaCache);
  const schema = Number.isFinite(sourceId) ? schemaCache[sourceId] : undefined;

  const [source, setSource] = useState<DpDataSource | null>(null);
  const [loadingSource, setLoadingSource] = useState(true);
  const [currentSql, setCurrentSql] = useState<string>('SELECT 1;');
  const [activeTab, setActiveTab] = useState<TabKey>('editor');
  const [executeResult, setExecuteResult] = useState<DpExecuteResponse | null>(null);
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    if (!Number.isFinite(sourceId)) {
      message.error('无效的数据源 ID');
      navigate('/data-platform/sources', { replace: true });
      return;
    }
    let cancelled = false;
    void (async () => {
      setLoadingSource(true);
      try {
        const s = await dataPlatformService.getSource(sourceId);
        if (!cancelled) setSource(s);
      } catch (err: unknown) {
        const anyErr = err as { message?: string };
        if (!cancelled) {
          message.error(anyErr.message ?? '加载数据源失败');
          navigate('/data-platform/sources', { replace: true });
        }
      } finally {
        if (!cancelled) setLoadingSource(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sourceId, navigate]);

  const handleColumnClick = (columnName: string): void => {
    setCurrentSql((prev) => {
      if (!prev) return columnName;
      const needsSpace = !/[\s(,]$/.test(prev);
      return prev + (needsSpace ? ' ' : '') + columnName;
    });
  };

  const applyToEditor = (sql: string): void => {
    setCurrentSql(sql);
    setActiveTab('editor');
  };

  if (loadingSource || !source) {
    return (
      <div>
        <PageHeader title="数据源详情" subtitle="加载中…" />
        <Skeleton active paragraph={{ rows: 6 }} />
      </div>
    );
  }

  const dialectLabel =
    source.dialect === 'mysql'
      ? 'MySQL'
      : source.dialect === 'postgresql'
        ? 'PostgreSQL'
        : source.dialect === 'sqlite'
          ? 'SQLite'
          : source.dialect === 'mysql_readonly'
            ? 'MySQL (只读)'
            : source.dialect;

  const tabItems = [
    {
      key: 'editor',
      label: 'SQL 编辑器',
      children: (
        <EditorTab
          source={source}
          schema={schema}
          sql={currentSql}
          onSqlChange={setCurrentSql}
          executeResult={executeResult}
          setExecuteResult={setExecuteResult}
          executing={executing}
          setExecuting={setExecuting}
        />
      ),
    },
    {
      key: 'chat',
      label: 'AI 对话',
      children: <ChatTab sourceId={source.id} onApplyToEditor={applyToEditor} />,
    },
    {
      key: 'history',
      label: '执行历史',
      children: <HistoryTab sourceId={source.id} onRerun={applyToEditor} />,
    },
    {
      key: 'saved',
      label: '保存的查询',
      children: <SavedQueriesTab sourceId={source.id} onRun={applyToEditor} />,
    },
  ];

  return (
    <div>
      <Breadcrumb
        style={{ marginBottom: 8 }}
        items={[
          { title: <Link to="/data-platform/sources">数据源</Link> },
          { title: source.name },
        ]}
      />
      <PageHeader
        title={source.name}
        subtitle={`${dialectLabel} · ${source.database}${
          source.host ? ` · ${source.host}${source.port ? `:${source.port}` : ''}` : ''
        }`}
      />

      <Row gutter={16} align="stretch">
        <Col xs={24} md={8} lg={7} xl={6} style={{ minWidth: 280 }}>
          <SchemaSidebar sourceId={source.id} onColumnClick={handleColumnClick} />
        </Col>
        <Col xs={24} md={16} lg={17} xl={18}>
          <Tabs
            activeKey={activeTab}
            onChange={(k) => setActiveTab(k as TabKey)}
            items={tabItems}
            destroyInactiveTabPane={false}
          />
        </Col>
      </Row>
    </div>
  );
}
