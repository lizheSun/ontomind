import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Tabs, Typography, message, App } from 'antd';
import {
  LockOutlined,
  UserOutlined,
  MailOutlined,
} from '@ant-design/icons';
import userService from '../services/user.service';

const { Text } = Typography;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function formatApiError(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
    return detail.message;
  }
  const messageStr = err?.response?.data?.message;
  if (typeof messageStr === 'string') return messageStr;
  if (err?.message === 'Network Error') {
    return '无法连接后端服务，请确认后端已启动且 CORS 配置正确';
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
      if (res.data.user) {
        localStorage.setItem('user', JSON.stringify(res.data.user));
      }
      message.success('登录成功');
      navigate('/');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      notification.error({
        message: '登录失败',
        description: formatApiError(err, '请检查用户名和密码'),
        placement: 'top',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: {
    username: string;
    email: string;
    password: string;
  }) => {
    setLoading(true);
    try {
      await userService.register(values);
      message.success('注册成功，请登录');
      setActiveTab('login');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      notification.error({
        message: '注册失败',
        description: formatApiError(err, '注册失败，请稍后重试'),
        placement: 'top',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--paper-01, #fafaf7)',
        position: 'relative',
        overflow: 'hidden',
        fontFamily: 'inherit',
      }}
    >
      {/* 极淡背景 dot */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'radial-gradient(circle, rgba(26,25,24,0.06) 0.5px, transparent 0.5px)',
          backgroundSize: '24px 24px',
          opacity: 0.5,
          pointerEvents: 'none',
        }}
      />

      {/* 登录卡片 */}
      <div
        style={{
          position: 'relative',
          zIndex: 1,
          width: 400,
          padding: '40px 36px',
          borderRadius: 14,
          background: 'var(--paper-00, #ffffff)',
          border: '1px solid var(--border-subtle, rgba(26,25,24,0.10))',
          boxShadow: 'var(--shadow-md, 0 4px 20px rgba(26,25,24,0.06))',
          opacity: mounted ? 1 : 0,
          transform: mounted ? 'translateY(0)' : 'translateY(12px)',
          transition:
            'opacity 0.6s cubic-bezier(0.16,1,0.3,1), transform 0.6s cubic-bezier(0.16,1,0.3,1)',
        }}
      >
        {/* Logo — editorial */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div
            style={{
              display: 'inline-block',
              fontFamily: "'Fraunces', serif",
              fontSize: 40,
              fontWeight: 500,
              color: 'var(--ink-100, #1a1918)',
              letterSpacing: '-0.02em',
              fontStyle: 'italic',
              lineHeight: 1,
              marginBottom: 8,
            }}
          >
            OntoMind
          </div>
          <div>
            <Text
              style={{
                color: 'var(--ink-40, #8f8b84)',
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
                textTransform: 'uppercase',
                letterSpacing: '0.16em',
              }}
            >
              专家团 · Editorial
            </Text>
          </div>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={(k) => setActiveTab(k as 'login' | 'register')}
          centered
          size="middle"
          style={{ marginBottom: 12 }}
          items={[
            { key: 'login', label: '登录' },
            { key: 'register', label: '注册' },
          ]}
        />

        {activeTab === 'login' ? (
          <Form onFinish={handleLogin} size="large" autoComplete="off">
            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input
                prefix={<UserOutlined style={{ color: 'var(--ink-40, #8f8b84)' }} />}
                placeholder="用户名"
                style={{ height: 44, borderRadius: 10 }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--ink-40, #8f8b84)' }} />}
                placeholder="密码"
                style={{ height: 44, borderRadius: 10 }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                style={{
                  height: 44,
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 500,
                }}
              >
                登录
              </Button>
            </Form.Item>
          </Form>
        ) : (
          <Form onFinish={handleRegister} size="large" autoComplete="off">
            <Form.Item
              name="username"
              rules={[
                { required: true, message: '请输入用户名' },
                { min: 3, message: '用户名至少3个字符' },
              ]}
            >
              <Input
                prefix={<UserOutlined style={{ color: 'var(--ink-40, #8f8b84)' }} />}
                placeholder="用户名"
                style={{ height: 44, borderRadius: 10 }}
              />
            </Form.Item>

            <Form.Item
              name="email"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '邮箱格式不正确' },
              ]}
            >
              <Input
                prefix={<MailOutlined style={{ color: 'var(--ink-40, #8f8b84)' }} />}
                placeholder="邮箱"
                style={{ height: 44, borderRadius: 10 }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少6个字符' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--ink-40, #8f8b84)' }} />}
                placeholder="密码"
                style={{ height: 44, borderRadius: 10 }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                style={{
                  height: 44,
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 500,
                }}
              >
                创建账号
              </Button>
            </Form.Item>
          </Form>
        )}

        <Text
          style={{
            display: 'block',
            textAlign: 'center',
            marginTop: 28,
            color: 'var(--ink-40, #8f8b84)',
            fontSize: 10,
            fontFamily: "'JetBrains Mono', monospace",
            letterSpacing: '0.12em',
          }}
        >
          v0.1.0
        </Text>
      </div>
    </div>
  );
}
