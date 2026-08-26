/**
 * AI 设置入口（阶段 3.2）
 *
 * 在资讯页工具栏展示 AI 配置状态 + 「AI 设置」按钮，点击弹出 Modal：
 * - 未配置：显示「AI 未配置」Tag，可输入 Key 保存
 * - 已配置：显示「AI 已配置」Tag + 掩码，可重新保存或清空
 *
 * 安全：后端只回传 has_key + masked_key，明文 Key 不落前端状态展示区。
 * 军规 6：保存/清空失败必弹提示，不静默。
 */
import { useCallback, useEffect, useState } from 'react';
import { App as AntdApp, Button, Input, Modal, Space, Tag, Typography } from 'antd';
import { KeyOutlined } from '@ant-design/icons';
import { clearAiConfig, getAiConfig, saveAiConfig } from '@/api/ai';
import type { AIConfigResponse } from '@/types/ai';

const { Text } = Typography;

export default function AiSettings() {
  const { message: messageApi, modal } = AntdApp.useApp();

  const [open, setOpen] = useState(false);
  const [configInfo, setConfigInfo] = useState<AIConfigResponse | null>(null);
  const [keyValue, setKeyValue] = useState('');
  const [saving, setSaving] = useState(false);

  // 挂载时拉取配置状态
  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = useCallback(async () => {
    try {
      setConfigInfo(await getAiConfig());
    } catch {
      // 后端不可用时，按未配置处理（不阻塞页面）
      setConfigInfo({ has_key: false, masked_key: '' });
    }
  }, []);

  const openModal = () => {
    setKeyValue('');
    setOpen(true);
  };

  const handleSave = async () => {
    const key = keyValue.trim();
    if (!key) {
      messageApi.warning('请输入 API Key');
      return;
    }
    setSaving(true);
    try {
      const info = await saveAiConfig({ api_key: key });
      setConfigInfo(info);
      messageApi.success('已保存 AI API Key');
      setOpen(false);
    } catch (err: any) {
      messageApi.error(err?.message || '保存失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  const handleClear = async () => {
    setSaving(true);
    try {
      const info = await clearAiConfig();
      setConfigInfo(info);
      messageApi.success('已清空 AI API Key');
      setOpen(false);
    } catch (err: any) {
      messageApi.error(err?.message || '清空失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  const confirmClear = () => {
    modal.confirm({
      title: '清空 AI API Key？',
      content: '清空后如需使用 AI 总结需重新填写。此操作不可恢复。',
      okText: '清空',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: handleClear,
    });
  };

  return (
    <>
      <Space>
        <Tag color={configInfo?.has_key ? 'success' : 'default'}>
          {configInfo?.has_key ? 'AI 已配置' : 'AI 未配置'}
        </Tag>
        <Button icon={<KeyOutlined />} onClick={openModal}>
          AI 设置
        </Button>
      </Space>

      <Modal
        title="AI 设置（智谱 API Key）"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={handleSave}
        okText="保存"
        cancelText="取消"
        confirmLoading={saving}
        width={480}
      >
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary" style={{ fontSize: 13 }}>
            AI 总结使用智谱免费模型 GLM-4-Flash，需要你自注册的 API Key（
            {statusHint()}
            ）。Key 仅保存在本机，不会上传。
          </Text>
        </div>

        {configInfo?.has_key && (
          <div style={{ marginBottom: 12 }}>
            <Tag color="success">当前已配置</Tag>
            <Text type="secondary">掩码：{configInfo.masked_key}</Text>
          </div>
        )}

        <Input.Password
          placeholder="输入智谱 API Key"
          value={keyValue}
          onChange={(e) => setKeyValue(e.target.value)}
          autoComplete="new-password"
          onPressEnter={handleSave}
        />

        <div style={{ marginTop: 12, textAlign: 'right' }}>
          {configInfo?.has_key ? (
            <Button danger size="small" onClick={confirmClear} disabled={saving}>
              清空当前 Key
            </Button>
          ) : null}
        </div>
      </Modal>
    </>
  );

  function statusHint(): string {
    return configInfo?.has_key ? '可重新保存以替换' : '首次使用需填写';
  }
}