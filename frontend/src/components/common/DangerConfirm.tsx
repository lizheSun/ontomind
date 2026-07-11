import { Modal } from 'antd';
import { ExclamationCircleFilled } from '@ant-design/icons';

interface DangerConfirmOptions {
  title: string;
  content?: React.ReactNode;
  okText?: string;
  cancelText?: string;
  onOk: () => void | Promise<void>;
  onCancel?: () => void;
}

/**
 * 危险操作二次确认（删除、清空等）。
 * 用法：DangerConfirm({ title: '确认删除该数据源？', content: '此操作不可撤销', onOk: () => handleDelete() });
 */
export const DangerConfirm = (opts: DangerConfirmOptions): void => {
  Modal.confirm({
    title: opts.title,
    icon: <ExclamationCircleFilled style={{ color: '#fb7185' }} />,
    content: opts.content,
    okText: opts.okText ?? '确认删除',
    okType: 'danger',
    cancelText: opts.cancelText ?? '取消',
    onOk: opts.onOk,
    onCancel: opts.onCancel,
    centered: true,
    maskClosable: false,
  });
};
