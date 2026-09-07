'use client';

import React, { useEffect, useState } from 'react';
import {
    Alert,
    Breadcrumb,
    Button,
    Card,
    Form,
    Input,
    Select,
    Space,
    Tag,
    Typography,
    message,
} from 'antd';
import {
    ApiOutlined,
    ArrowLeftOutlined,
    ExperimentOutlined,
    SaveOutlined,
    SettingOutlined,
    SoundOutlined,
} from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import LlmModelSelect from '@/components/Admin/LlmModelSelect';
import { llmModelsHint, pickModelForProvider, useLlmModels } from '@/hooks/useLlmModels';
import { settingsService, SystemLLMSettings } from '@/services/settingsService';

const { Title, Paragraph, Text } = Typography;

export default function SystemSettingsPage() {
    const router = useRouter();
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [settings, setSettings] = useState<SystemLLMSettings | null>(null);
    const watchedUrl = Form.useWatch('llm_api_base_url', form);
    const watchedKey = Form.useWatch('llm_api_key', form);
    const {
        models: llmModels,
        loading: loadingModels,
        error: modelsError,
        reload: reloadModels,
    } = useLlmModels({
        apiBaseUrl: watchedUrl,
        apiKey: watchedKey,
        maskedKey: settings?.llm_api_key_masked,
        enabled: !loading,
    });
    const providerKeyRef = React.useRef<string | undefined>(undefined);

    const loadSettings = async () => {
        setLoading(true);
        try {
            const data = await settingsService.getSettings();
            setSettings(data);
            form.setFieldsValue({
                llm_api_base_url: data.llm_api_base_url,
                llm_api_key: data.llm_api_key_masked || '',
                llm_model_name: data.llm_model_name,
                tts_voice: data.tts_voice || 'vi-VN-HoaiMyNeural',
            });
        } catch (error: unknown) {
            console.error(error);
            message.error('Không thể tải cài đặt hệ thống');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadSettings();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (!llmModels.length) return;
        const providerKey = `${(watchedUrl || '').trim()}|${(watchedKey || '').trim()}`;
        const providerChanged = providerKeyRef.current !== undefined && providerKeyRef.current !== providerKey;
        providerKeyRef.current = providerKey;
        const next = pickModelForProvider(
            llmModels,
            form.getFieldValue('llm_model_name'),
            undefined,
            providerChanged,
        );
        if (next && next !== form.getFieldValue('llm_model_name')) {
            form.setFieldsValue({ llm_model_name: next });
        }
    }, [llmModels, watchedUrl, watchedKey, form]);

    const onSave = async (values: {
        llm_api_base_url: string;
        llm_api_key?: string;
        llm_model_name: string;
        tts_voice?: string;
    }) => {
        setSaving(true);
        try {
            const key = values.llm_api_key?.trim();
            const payload: {
                llm_api_base_url: string;
                llm_model_name: string;
                llm_api_key?: string;
                tts_voice?: string;
            } = {
                llm_api_base_url: values.llm_api_base_url.trim(),
                llm_model_name: values.llm_model_name.trim(),
                tts_voice: values.tts_voice,
            };
            if (key && key !== settings?.llm_api_key_masked) {
                payload.llm_api_key = key;
            }
            const updated = await settingsService.updateSettings(payload);
            setSettings(updated);
            form.setFieldsValue({
                llm_api_base_url: updated.llm_api_base_url,
                llm_api_key: updated.llm_api_key_masked || '',
                llm_model_name: updated.llm_model_name,
                tts_voice: updated.tts_voice || 'vi-VN-HoaiMyNeural',
            });
            message.success('Đã lưu cài đặt hệ thống');
        } catch (error: unknown) {
            const axiosError = error as { response?: { data?: { detail?: string } } };
            message.error(axiosError.response?.data?.detail || 'Không thể lưu cài đặt');
        } finally {
            setSaving(false);
        }
    };

    const onTest = async () => {
        try {
            await form.validateFields(['llm_api_base_url']);
            setTesting(true);
            const result = await reloadModels();
            if (result.ok) {
                const count = result.models.length;
                message.success(
                    count
                        ? `Kết nối thành công. Provider trả về ${count} model.`
                        : 'Kết nối thành công.'
                );
                if (count && !form.getFieldValue('llm_model_name')) {
                    form.setFieldsValue({ llm_model_name: result.models[0] });
                }
            } else {
                message.error(result.error || 'Không kết nối được tới endpoint');
            }
        } catch (error: unknown) {
            if (error && typeof error === 'object' && 'errorFields' in error) {
                return;
            }
            message.error('Không thể kiểm tra kết nối');
        } finally {
            setTesting(false);
        }
    };

    return (
        <AuthGuard requiredRole="admin">
            <MainLayout>
                <div style={{ background: '#f5f5f5', minHeight: '100vh', margin: -24, padding: 32 }}>
                    <div style={{ maxWidth: 800, margin: '0 auto 24px' }}>
                        <Breadcrumb
                            items={[
                                { title: 'Dashboard', href: '/dashboard' },
                                { title: 'Admin' },
                                { title: 'Cài đặt hệ thống' },
                            ]}
                        />
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 16 }}>
                            <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()} type="text" />
                            <SettingOutlined style={{ fontSize: 22, color: '#1677ff' }} />
                            <Title level={3} style={{ margin: 0 }}>Cài đặt hệ thống</Title>
                            {settings && (
                                <Tag color={settings.source === 'database' ? 'blue' : 'default'}>
                                    {settings.source === 'database' ? 'Đã lưu trên server' : 'Đang dùng .env'}
                                </Tag>
                            )}
                        </div>
                        <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                            Endpoint mặc định cho mọi chatbot. Từng bot có thể ghi đè bằng endpoint + API key riêng.
                        </Paragraph>
                    </div>

                    <div style={{ maxWidth: 800, margin: '0 auto' }}>
                        <Alert
                            type="info"
                            showIcon
                            style={{ marginBottom: 16, borderRadius: 8 }}
                            message="Endpoint và API key phải cùng một nhà cung cấp"
                            description="Key Gemini chỉ chạy với endpoint Gemini, key OpenAI với OpenAI, Ollama với Ollama. Chỉ nhập API key mà không đổi endpoint thì key vẫn gửi tới provider mặc định — bên kia sẽ từ chối."
                        />

                        <Card
                            loading={loading}
                            title={
                                <Space>
                                    <ApiOutlined />
                                    <span>LLM provider mặc định</span>
                                </Space>
                            }
                            style={{ borderRadius: 8 }}
                            styles={{ header: { borderBottom: '2px solid #1677ff' } }}
                        >
                            <Form
                                form={form}
                                layout="vertical"
                                onFinish={onSave}
                                disabled={loading}
                            >
                                <Form.Item
                                    name="llm_api_base_url"
                                    label="LLM Endpoint"
                                    extra="OpenAI-compatible, ví dụ: http://localhost:11434/v1 hoặc https://generativelanguage.googleapis.com/v1beta/openai/"
                                    rules={[
                                        { required: true, message: 'Nhập endpoint' },
                                        {
                                            pattern: /^https?:\/\/.+/i,
                                            message: 'Endpoint phải bắt đầu bằng http:// hoặc https://',
                                        },
                                    ]}
                                >
                                    <Input
                                        size="large"
                                        placeholder="https://api.openai.com/v1"
                                    />
                                </Form.Item>

                                <Form.Item
                                    name="llm_api_key"
                                    label="API Key hệ thống"
                                    extra="Để nguyên giá trị ẩn nếu không đổi key. Ollama local có thể để trống hoặc ollama."
                                >
                                    <Input.Password
                                        size="large"
                                        placeholder="sk-... hoặc để trống với Ollama"
                                    />
                                </Form.Item>

                                <Form.Item
                                    name="llm_model_name"
                                    label="Model mặc định"
                                    extra={llmModelsHint(loadingModels, modelsError, llmModels.length)}
                                    rules={[{ required: true, message: 'Chọn hoặc nhập tên model mặc định' }]}
                                >
                                    <LlmModelSelect models={llmModels} loading={loadingModels} />
                                </Form.Item>

                                <Form.Item
                                    name="tts_voice"
                                    label={
                                        <Space>
                                            <SoundOutlined />
                                            <span>Giọng đọc Live</span>
                                        </Space>
                                    }
                                    extra="Giọng Edge-TTS dùng khi bot đọc câu trả lời. Prefetch câu kế để tránh ngắt giữa chừng."
                                    rules={[{ required: true, message: 'Chọn giọng đọc' }]}
                                >
                                    <Select
                                        size="large"
                                        options={[
                                            { value: 'vi-VN-HoaiMyNeural', label: 'Hoài My (nữ)' },
                                            { value: 'vi-VN-NamMinhNeural', label: 'Nam Minh (nam)' },
                                        ]}
                                    />
                                </Form.Item>

                                <Space wrap>
                                    <Button
                                        type="primary"
                                        htmlType="submit"
                                        icon={<SaveOutlined />}
                                        loading={saving}
                                        size="large"
                                    >
                                        Lưu cài đặt
                                    </Button>
                                    <Button
                                        htmlType="button"
                                        icon={<ExperimentOutlined />}
                                        onClick={onTest}
                                        loading={testing}
                                        size="large"
                                    >
                                        Kiểm tra kết nối
                                    </Button>
                                </Space>
                            </Form>

                            {settings?.updated_at && (
                                <Text type="secondary" style={{ display: 'block', marginTop: 16 }}>
                                    Cập nhật lần cuối: {new Date(settings.updated_at).toLocaleString('vi-VN')}
                                </Text>
                            )}
                        </Card>
                    </div>
                </div>
            </MainLayout>
        </AuthGuard>
    );
}
