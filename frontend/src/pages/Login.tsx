import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, message, App } from 'antd';
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  MoonOutlined,
  SunOutlined,
  RocketOutlined,
  LinkOutlined,
  CloudOutlined,
  CodeOutlined,
  ApiOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import userService from '../services/user.service';
import { BrandMark } from '../components/common/BrandMark';
import { applyColorMode, readColorMode, setColorMode, type ColorMode } from '../theme';

function formatApiError(err: unknown, fallback: string): string {
  const e = err as { response?: { data?: { detail?: unknown; message?: string } }; code?: string; message?: string };
  const detail = e?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail && typeof (detail as { message: unknown }).message === 'string') {
    return String((detail as { message: string }).message);
  }
  const msg = e?.response?.data?.message;
  if (typeof msg === 'string') return msg;
  if (!e?.response) {
    const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
    if (e?.code === 'ECONNABORTED' || e?.message?.includes('timeout'))
      return `请求超时（30s）。后端 ${base} 可能负载过高或卡住。`;
    return `连不上后端 ${base}（已自动重试 3 次）。请检查后端是否在跑。`;
  }
  return e?.message || fallback;
}

export default function Login() {
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [mode, setMode] = useState<ColorMode>(() => readColorMode());
  const authRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { notification } = App.useApp();

  useEffect(() => {
    applyColorMode(mode);
  }, [mode]);

  useEffect(() => {
    if (showAuth) authRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [showAuth]);

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const res = await userService.login(values);
      localStorage.setItem('access_token', res.data.accessToken);
      if (res.data.user) localStorage.setItem('user', JSON.stringify(res.data.user));
      message.success('登录成功');
      navigate('/');
    } catch (err: unknown) {
      notification.error({
        message: '登录失败',
        description: <span style={{ whiteSpace: 'pre-line', fontSize: 12.5, lineHeight: 1.7 }}>{formatApiError(err, '请检查用户名和密码')}</span>,
        placement: 'top',
        duration: 8,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: { username: string; email: string; password: string }) => {
    setLoading(true);
    try {
      await userService.register(values);
      message.success('注册成功，请登录');
      setActiveTab('login');
    } catch (err: unknown) {
      notification.error({
        message: '注册失败',
        description: <span style={{ whiteSpace: 'pre-line', fontSize: 12.5, lineHeight: 1.7 }}>{formatApiError(err, '注册失败，请稍后重试')}</span>,
        placement: 'top',
        duration: 8,
      });
    } finally {
      setLoading(false);
    }
  };

  const toggleTheme = () => {
    const next = mode === 'dark' ? 'light' : 'dark';
    setColorMode(next);
    setMode(next);
  };

  return (
    <div className="om-welcome">
      <div className="om-welcome-bar">
        <button type="button" className="om-rail-item" onClick={toggleTheme} aria-label="切换主题" style={{ width: 30, height: 30 }}>
          {mode === 'dark' ? <SunOutlined /> : <MoonOutlined />}
        </button>
      </div>

      <header className="om-welcome-hero">
        <div className="om-welcome-logo-wrap">
          <BrandMark size={48} />
        </div>
        <h1 className="om-welcome-title">欢迎使用 OntoMind</h1>
        <p className="om-welcome-sub">把数据、Agent 与算力放在一处，随时待命。</p>
        <div className="om-welcome-actions">
          <button type="button" className="om-pill om-pill-primary" onClick={() => setShowAuth(true)}>
            <RocketOutlined /> 开始使用
          </button>
          <button
            type="button"
            className="om-pill om-pill-ghost"
            onClick={() => document.getElementById('om-welcome-cards')?.scrollIntoView({ behavior: 'smooth' })}
          >
            <LinkOutlined /> 了解平台
          </button>
        </div>
      </header>

      {showAuth && (
        <div ref={authRef} className="om-welcome-auth">
          <div style={{ display: 'flex', marginBottom: 20, borderBottom: '1px solid var(--border-hairline)' }}>
            {(['login', 'register'] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                style={{
                  flex: 1,
                  padding: '10px 0',
                  fontSize: 14,
                  fontWeight: activeTab === tab ? 500 : 400,
                  color: activeTab === tab ? 'var(--accent)' : 'var(--text-tertiary)',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: activeTab === tab ? '2px solid var(--accent)' : '2px solid transparent',
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                {tab === 'login' ? '登录' : '注册'}
              </button>
            ))}
          </div>
          {activeTab === 'login' ? (
            <Form onFinish={handleLogin} size="large" layout="vertical">
              <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]} style={{ marginBottom: 14 }}>
                <Input prefix={<UserOutlined style={{ color: 'var(--text-tertiary)' }} />} placeholder="用户名" />
              </Form.Item>
              <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]} style={{ marginBottom: 20 }}>
                <Input.Password prefix={<LockOutlined style={{ color: 'var(--text-tertiary)' }} />} placeholder="密码" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block size="large">
                继续
              </Button>
            </Form>
          ) : (
            <Form onFinish={handleRegister} size="large" layout="vertical">
              <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }, { min: 3, message: '用户名至少3个字符' }]} style={{ marginBottom: 14 }}>
                <Input prefix={<UserOutlined style={{ color: 'var(--text-tertiary)' }} />} placeholder="用户名" />
              </Form.Item>
              <Form.Item name="email" rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '邮箱格式不正确' }]} style={{ marginBottom: 14 }}>
                <Input prefix={<MailOutlined style={{ color: 'var(--text-tertiary)' }} />} placeholder="邮箱" />
              </Form.Item>
              <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少6个字符' }]} style={{ marginBottom: 20 }}>
                <Input.Password prefix={<LockOutlined style={{ color: 'var(--text-tertiary)' }} />} placeholder="密码" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block size="large">
                创建账号
              </Button>
            </Form>
          )}
        </div>
      )}

      <div className="om-welcome-banner">
        <CloudOutlined style={{ color: 'var(--accent)', fontSize: 18 }} />
        <span style={{ flex: 1 }}>
          OntoMind 工作台：编码、数据、Agent 与算力，<strong>统一账号</strong>进入。
        </span>
        <button type="button" className="om-welcome-badge om-welcome-badge-rec" style={{ border: 'none', cursor: 'pointer', height: 28, padding: '0 12px' }} onClick={() => { setShowAuth(true); setActiveTab('register'); }}>
          注册获取
        </button>
      </div>

      <div id="om-welcome-cards" className="om-welcome-cards">
        <article className="om-welcome-card om-welcome-card--primary">
          <span className="om-welcome-badge om-welcome-badge-rec">推荐</span>
          <CodeOutlined style={{ fontSize: 36, color: 'var(--accent)' }} />
          <h3>AIDE</h3>
          <p>OpenCode 编码环境，容器即工作区，随时指挥你的 AI 写代码。</p>
          <Button type="primary" block onClick={() => setShowAuth(true)}>开始使用</Button>
        </article>
        <article className="om-welcome-card">
          <span className="om-welcome-badge om-welcome-badge-req">工作台</span>
          <ApiOutlined style={{ fontSize: 36, color: 'var(--accent)' }} />
          <h3>AgentOps</h3>
          <p>设计 Agent / Skill，编排方案并发布到算力节点。</p>
          <Button block onClick={() => setShowAuth(true)}>了解更多</Button>
        </article>
        <article className="om-welcome-card">
          <span className="om-welcome-badge om-welcome-badge-ok"><CheckCircleOutlined /> 数据层</span>
          <DatabaseOutlined style={{ fontSize: 36, color: '#6c757d' }} />
          <h3>DataOps</h3>
          <p>仓库、知识库、元数据标注与本体建模，从资产到语义层。</p>
          <div style={{ color: '#00c853', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
            <CheckCircleOutlined /> 已接入
          </div>
        </article>
      </div>

      <div className="om-welcome-foot">OntoMind</div>
    </div>
  );
}
