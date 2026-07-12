import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Tabs, Typography, message, App } from 'antd';
import {
  LockOutlined,
  UserOutlined,
  MailOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import userService from '../services/user.service';

const { Title, Text } = Typography;

function formatApiError(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
    return detail.message;
  }
  const message = err?.response?.data?.message;
  if (typeof message === 'string') return message;
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
        background: '#060b14',
        position: 'relative',
        overflow: 'hidden',
        fontFamily: 'inherit',
      }}
    >
      {/* 背景动效 */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'radial-gradient(circle, rgba(59,130,246,0.08) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
          opacity: 0.5,
        }}
      />

      {/* 模糊光球 */}
      <div
        style={{
          position: 'absolute',
          width: 600,
          height: 600,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%)',
          top: -200,
          right: -150,
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 500,
          height: 500,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)',
          bottom: -150,
          left: -100,
          pointerEvents: 'none',
        }}
      />

      {/* 登录卡片 */}
      <div
        style={{
          position: 'relative',
          zIndex: 1,
          width: 420,
          padding: '40px 36px',
          borderRadius: 20,
          background:
            'linear-gradient(145deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)',
          border: '1px solid rgba(255,255,255,0.08)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
          opacity: mounted ? 1 : 0,
          transform: mounted ? 'translateY(0)' : 'translateY(16px)',
          transition: 'opacity 0.6s cubic-bezier(0.16,1,0.3,1), transform 0.6s cubic-bezier(0.16,1,0.3,1)',
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: 14,
              background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 16,
              boxShadow: '0 8px 24px rgba(59,130,246,0.3)',
            }}
          >
            <RocketOutlined style={{ fontSize: 24, color: '#fff' }} />
          </div>
          <Title
            level={3}
            style={{ color: '#e8eef5', margin: 0, fontWeight: 700, letterSpacing: -0.5 }}
          >
            OntoMind
          </Title>
          <Text style={{ color: '#506380', fontSize: 13 }}>
            智能知识引擎
          </Text>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={(k) => setActiveTab(k as 'login' | 'register')}
          centered
          size="large"
          style={{ marginBottom: 8 }}
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
                prefix={<UserOutlined style={{ color: '#506380' }} />}
                placeholder="用户名"
                style={{
                  height: 46,
                  borderRadius: 12,
                  background: 'rgba(255,255,255,0.03)',
                }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: '#506380' }} />}
                placeholder="密码"
                style={{
                  height: 46,
                  borderRadius: 12,
                  background: 'rgba(255,255,255,0.03)',
                }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                style={{
                  height: 46,
                  borderRadius: 12,
                  fontSize: 15,
                  fontWeight: 600,
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
                prefix={<UserOutlined style={{ color: '#506380' }} />}
                placeholder="用户名"
                style={{
                  height: 46,
                  borderRadius: 12,
                  background: 'rgba(255,255,255,0.03)',
                }}
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
                prefix={<MailOutlined style={{ color: '#506380' }} />}
                placeholder="邮箱"
                style={{
                  height: 46,
                  borderRadius: 12,
                  background: 'rgba(255,255,255,0.03)',
                }}
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
                prefix={<LockOutlined style={{ color: '#506380' }} />}
                placeholder="密码"
                style={{
                  height: 46,
                  borderRadius: 12,
                  background: 'rgba(255,255,255,0.03)',
                }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                style={{
                  height: 46,
                  borderRadius: 12,
                  fontSize: 15,
                  fontWeight: 600,
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
            marginTop: 24,
            color: '#405070',
            fontSize: 11,
          }}
        >
          OntoMind · 版本 0.1.0
        </Text>
      </div>
    </div>
  );
}
