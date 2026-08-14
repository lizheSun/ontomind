import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, message, App } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';

import userService from '../services/user.service';



function formatApiError(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && typeof detail.message === 'string') return detail.message;
  const msg = err?.response?.data?.message;
  if (typeof msg === 'string') return msg;
  if (!err?.response) {
    const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
    if (err?.code === 'ECONNABORTED' || err?.message?.includes('timeout'))
      return `请求超时（30s）。后端 ${base} 可能负载过高或卡住。`;
    return `连不上后端 ${base}（已自动重试 3 次）。请检查后端是否在跑。`;
  }
  return err?.message || fallback;
}

export default function Login() {
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const navigate = useNavigate();
  const { notification } = App.useApp();

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 80);
    return () => clearTimeout(t);
  }, []);

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const res = await userService.login(values);
      localStorage.setItem('access_token', res.data.accessToken);
      if (res.data.user) localStorage.setItem('user', JSON.stringify(res.data.user));
      message.success('登录成功');
      navigate('/');
    } catch (err: any) {
      notification.error({
        message: '登录失败',
        description: <span style={{ whiteSpace: 'pre-line', fontSize: 12.5, lineHeight: 1.7 }}>{formatApiError(err, '请检查用户名和密码')}</span>,
        placement: 'top', duration: 8,
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
    } catch (err: any) {
      notification.error({
        message: '注册失败',
        description: <span style={{ whiteSpace: 'pre-line', fontSize: 12.5, lineHeight: 1.7 }}>{formatApiError(err, '注册失败，请稍后重试')}</span>,
        placement: 'top', duration: 8,
      });
    } finally {
      setLoading(false);
    }
  };

  /* 【UI 重构】Apple 登录页：纯白画布 + 大面积留白 + SF 字体层级 + Apple Blue 主色 */

  const tabBtnStyle = (active: boolean): React.CSSProperties => ({
    flex: 1,
    padding: '12px 0',
    fontSize: 14,
    fontWeight: active ? 600 : 400,
    color: active ? '#1d1d1f' : '#86868b',
    background: 'transparent',
    border: 'none',
    borderBottom: active ? '2px solid #0071e3' : '2px solid transparent',
    cursor: 'pointer',
    transition: 'all .18s ease',
    letterSpacing: '-0.01em',
  });

  const inputStyle: React.CSSProperties = {
    height: 48,
    borderRadius: 12,
    fontSize: 15,
    border: '1px solid rgba(0,0,0,0.12)',
    background: '#FFFFFF',
    padding: '0 16px',
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#F5F5F7', /* 【UI 重构】Apple 浅灰底 */
      padding: 24,
    }}>
      <div style={{
        width: 380, maxWidth: '100%',
        opacity: mounted ? 1 : 0,
        transform: mounted ? 'translateY(0)' : 'translateY(8px)',
        transition: 'opacity .7s ease, transform .7s ease',
      }}>
        {/* 【UI 重构】Logo：SF Pro Display 粗体 + Apple Blue 点缀 */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{
            fontFamily: "var(--font-sans, -apple-system, 'SF Pro Display', sans-serif)",
            fontSize: 34, fontWeight: 700,
            color: '#1d1d1f', letterSpacing: '-0.03em',
            lineHeight: 1.1, marginBottom: 6,
          }}>
            OntoMind
          </div>
          <div style={{
            fontSize: 13, color: '#86868b', fontFamily: "var(--font-sans, -apple-system, sans-serif)",
            fontWeight: 400, letterSpacing: '0.02em',
          }}>
            AI 领域工程平台
          </div>
        </div>

        {/* 【UI 重构】Apple 风格卡片容器：白底 + 柔和阴影 + 大圆角 */}
        <div style={{
          background: '#FFFFFF',
          borderRadius: 22,
          padding: '28px 24px 22px',
          boxShadow: '0 4px 24px rgba(0,0,0,0.05)',
          border: '1px solid rgba(0,0,0,0.06)',
        }}>
          {/* Tab 切换 */}
          <div style={{ display: 'flex', marginBottom: 24 }}>
            <button style={tabBtnStyle(activeTab === 'login')} onClick={() => setActiveTab('login')}>
              登录
            </button>
            <button style={tabBtnStyle(activeTab === 'register')} onClick={() => setActiveTab('register')}>
              注册
            </button>
          </div>

          {activeTab === 'login' ? (
            <Form onFinish={handleLogin} size="large" layout="vertical">
              <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]} style={{ marginBottom: 14 }}>
                <Input
                  prefix={<UserOutlined style={{ color: '#86868b' }} />}
                  placeholder="用户名"
                  style={inputStyle}
                />
              </Form.Item>
              <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]} style={{ marginBottom: 24 }}>
                <Input.Password
                  prefix={<LockOutlined style={{ color: '#86868b' }} />}
                  placeholder="密码"
                  style={inputStyle}
                />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block style={{
                height: 48, borderRadius: 12, fontSize: 15, fontWeight: 600,
                letterSpacing: '-0.01em',
              }}>
                登录
              </Button>
              <div style={{ textAlign: 'center', marginTop: 18 }}>
                <a onClick={() => setActiveTab('register')} style={{
                  color: '#0071e3', fontSize: 13, cursor: 'pointer', fontWeight: 500,
                  transition: 'color .18s ease',
                }}
                onMouseEnter={(e) => e.currentTarget.style.color = '#0077ED'}
                onMouseLeave={(e) => e.currentTarget.style.color = '#0071e3'}
                >还没有账号？创建新账号</a>
              </div>
            </Form>
          ) : (
            <Form onFinish={handleRegister} size="large" layout="vertical">
              <Form.Item name="username" rules={[
                { required: true, message: '请输入用户名' },
                { min: 3, message: '用户名至少3个字符' },
              ]} style={{ marginBottom: 14 }}>
                <Input
                  prefix={<UserOutlined style={{ color: '#86868b' }} />}
                  placeholder="用户名"
                  style={inputStyle}
                />
              </Form.Item>
              <Form.Item name="email" rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '邮箱格式不正确' },
              ]} style={{ marginBottom: 14 }}>
                <Input
                  prefix={<MailOutlined style={{ color: '#86868b' }} />}
                  placeholder="邮箱"
                  style={inputStyle}
                />
              </Form.Item>
              <Form.Item name="password" rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少6个字符' },
              ]} style={{ marginBottom: 24 }}>
                <Input.Password
                  prefix={<LockOutlined style={{ color: '#86868b' }} />}
                  placeholder="密码"
                  style={inputStyle}
                />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block style={{
                height: 48, borderRadius: 12, fontSize: 15, fontWeight: 600,
                letterSpacing: '-0.01em',
              }}>
                创建账号
              </Button>
              <div style={{ textAlign: 'center', marginTop: 18 }}>
                <a onClick={() => setActiveTab('login')} style={{
                  color: '#0071e3', fontSize: 13, cursor: 'pointer', fontWeight: 500,
                  transition: 'color .18s ease',
                }}
                onMouseEnter={(e) => e.currentTarget.style.color = '#0077ED'}
                onMouseLeave={(e) => e.currentTarget.style.color = '#0071e3'}
                >已有账号？登录</a>
              </div>
            </Form>
          )}
        </div>

        {/* 【UI 重构】版本号：极淡色，克制存在感 */}
        <div style={{ textAlign: 'center', marginTop: 28 }}>
          <span style={{
            color: '#86868b', fontSize: 11,
            fontFamily: "var(--font-sans, -apple-system, sans-serif)",
            letterSpacing: '0.04em',
          }}>v0.1.0</span>
        </div>
      </div>
    </div>
  );
}
