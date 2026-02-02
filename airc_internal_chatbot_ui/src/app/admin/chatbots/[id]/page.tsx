'use client';

import React, { useEffect, useState } from 'react';
import {
    Form,
    Input,
    Button,
    Select,
    Card,
    message,
    InputNumber,
    Spin,
    Tooltip,
    Breadcrumb,
    Slider,
    Radio,
    Alert,
    Tag,
    Row,
    Col
} from 'antd';
import {
    RobotOutlined,
    SaveOutlined,
    ArrowLeftOutlined,
    QuestionCircleOutlined,
    LockOutlined
} from '@ant-design/icons';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import { chatbotService } from '@/services/chatbotService';
import datasetService from '@/services/datasetService';
import { Chatbot, ChatbotUpdate } from '@/types/chatbot';
import { Dataset } from '@/core/entities/Dataset';
import { useRouter, useParams } from 'next/navigation';

const { Option } = Select;
const { TextArea } = Input;

// RAG Pipeline steps visualization
const ragPipelineSteps = [
    { step: 1, label: 'Query', desc: 'Câu hỏi', color: '#1890ff' },
    { step: 2, label: 'Embedding', desc: 'Vector hóa', color: '#52c41a' },
    { step: 3, label: 'Retrieval', desc: 'Tìm kiếm', color: '#13c2c2' },
    { step: 4, label: 'Reranking', desc: 'Sắp xếp lại', color: '#722ed1' },
    { step: 5, label: 'Generation', desc: 'Sinh câu trả lời', color: '#fa8c16' },
];

export default function EditChatbotPage() {
    const params = useParams();
    const router = useRouter();
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [chatbot, setChatbot] = useState<Chatbot | null>(null);
    const [datasets, setDatasets] = useState<Dataset[]>([]);
    const [rolesWithChatbot, setRolesWithChatbot] = useState<string[]>([]);

    // Watch no_context_behavior for conditional rendering
    const noContextBehavior = Form.useWatch('no_context_behavior', form);

    // Get ID from params (could be string or array)
    const id = Array.isArray(params?.id) ? params.id[0] : params?.id;

    useEffect(() => {
        if (id) {
            fetchData(id);
        }
    }, [id]);

    const fetchData = async (chatbotId: string) => {
        setLoading(true);
        try {
            // Fetch data
            const [botData, datasetsData, roles] = await Promise.all([
                chatbotService.getChatbot(chatbotId),
                datasetService.getDatasets(),
                chatbotService.getRolesWithChatbot(chatbotId), // exclude current chatbot
            ]);

            setChatbot(botData);
            setDatasets(datasetsData);
            setRolesWithChatbot(roles);

            // Set form values from chatbot data
            form.setFieldsValue({
                name: botData.name,
                description: botData.description,
                icon: botData.icon,
                visibility: botData.visibility,
                allowed_roles: botData.allowed_roles,
                dataset_ids: botData.dataset_ids,
                // Config - Embedding (fixed)
                embedding_model: botData.config.embedding_model || 'vietnamese-sbert',
                // Config - Retrieval
                search_mode: botData.config.search_mode || 'hybrid',
                top_k: botData.config.top_k || 5,
                similarity_threshold: botData.config.similarity_threshold || 0.5,
                // Config - Reranking
                reranker: botData.config.reranker || 'ms-marco-MiniLM-L-6-v2',
                rerank_top_n: botData.config.rerank_top_n,
                // Config - LLM
                model: botData.config.model || 'models/gemini-2.5-flash',
                api_key: botData.config.api_key,
                temperature: botData.config.temperature ?? 0.7,
                max_tokens: botData.config.max_tokens || 2048,
                system_prompt: botData.config.system_prompt,
                // Config - No context behavior
                no_context_behavior: botData.config.no_context_behavior || 'reject',
                no_context_message: botData.config.no_context_message,
            });
        } catch (error) {
            console.error('Error fetching data:', error);
            message.error('Không thể tải dữ liệu chatbot');
            router.push('/admin/chatbots');
        } finally {
            setLoading(false);
        }
    };

    const onFinish = async (values: any) => {
        if (!id) return;

        setSaving(true);
        try {
            const payload: ChatbotUpdate = {
                name: values.name,
                description: values.description,
                icon: values.icon,
                visibility: values.visibility,
                allowed_roles: values.allowed_roles,
                dataset_ids: values.dataset_ids,
                config: {
                    // Embedding (fixed)
                    embedding_model: values.embedding_model,
                    // Retrieval
                    search_mode: values.search_mode,
                    top_k: values.top_k,
                    similarity_threshold: values.similarity_threshold,
                    // Reranking
                    reranker: values.reranker,
                    rerank_top_n: values.rerank_top_n,
                    // LLM
                    model: values.model,
                    api_key: values.api_key,
                    temperature: values.temperature,
                    max_tokens: values.max_tokens,
                    system_prompt: values.system_prompt,
                    // No context behavior
                    no_context_behavior: values.no_context_behavior,
                    no_context_message: values.no_context_behavior === 'custom_message' ? values.no_context_message : null,
                },
            };

            await chatbotService.updateChatbot(id, payload);
            message.success('Cập nhật chatbot thành công!');
            router.push('/admin/chatbots');
        } catch (error: any) {
            message.error(error.response?.data?.detail || 'Có lỗi xảy ra');
        } finally {
            setSaving(false);
        }
    };

    const onFinishFailed = (errorInfo: any) => {
        message.error('Vui lòng kiểm tra lại các trường bắt buộc');
        console.log('Validation failed:', errorInfo);
    };

    if (loading) {
        return (
            <MainLayout>
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
                    <Spin size="large" tip="Đang tải dữ liệu chatbot..." />
                </div>
            </MainLayout>
        );
    }

    return (
        <AuthGuard>
            <MainLayout>
                <div style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
                    {/* Header */}
                    <div style={{ marginBottom: 24 }}>
                        <Breadcrumb
                            items={[
                                { title: 'Dashboard', href: '/dashboard' },
                                { title: 'Admin' },
                                { title: 'Chatbots', href: '/admin/chatbots' },
                                { title: 'Chỉnh sửa' },
                            ]}
                        />
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 16 }}>
                            <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()} type="text" />
                            <RobotOutlined style={{ fontSize: 28, color: '#1890ff' }} />
                            <h1 style={{ margin: 0, fontSize: 24, fontWeight: 600 }}>
                                Chỉnh sửa Chatbot: {chatbot?.name}
                            </h1>
                        </div>
                    </div>

                    {/* RAG Pipeline Visualization */}
                    <div style={{ marginBottom: 32 }}>
                        <Card
                            size="small"
                            style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', borderRadius: 12 }}
                            styles={{ body: { padding: '16px 24px' } }}
                        >
                            <div style={{ color: '#fff', fontWeight: 500, marginBottom: 12 }}>RAG Pipeline Flow</div>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                {ragPipelineSteps.map((item, idx) => (
                                    <React.Fragment key={item.step}>
                                        <div style={{ textAlign: 'center', minWidth: 80 }}>
                                            <div style={{
                                                width: 36, height: 36, borderRadius: '50%',
                                                background: item.color, color: '#fff',
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                fontWeight: 600, fontSize: 14, margin: '0 auto 8px'
                                            }}>{item.step}</div>
                                            <div style={{ fontWeight: 500, fontSize: 13, color: '#fff' }}>{item.label}</div>
                                            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.7)' }}>{item.desc}</div>
                                        </div>
                                        {idx < 4 && (
                                            <div style={{ flex: 1, height: 2, background: 'rgba(255,255,255,0.3)', margin: '0 8px', marginBottom: 24 }} />
                                        )}
                                    </React.Fragment>
                                ))}
                            </div>
                        </Card>
                    </div>

                    {/* Main Form */}
                    <div style={{ maxWidth: 800, margin: '0 auto' }}>
                        <Form
                            form={form}
                            layout="vertical"
                            onFinish={onFinish}
                            onFinishFailed={onFinishFailed}
                            scrollToFirstError
                        >
                            {/* SECTION 1: THÔNG TIN CƠ BẢN */}
                            <Card
                                title="Thông tin cơ bản"
                                style={{ marginBottom: 24, borderRadius: 8 }}
                                styles={{ header: { borderBottom: '2px solid #1890ff' } }}
                            >
                                <Form.Item
                                    name="name"
                                    label="Tên Chatbot"
                                    rules={[
                                        { required: true, message: 'Vui lòng nhập tên' },
                                        { min: 3, message: 'Tối thiểu 3 ký tự' }
                                    ]}
                                >
                                    <Input placeholder="VD: Trợ lý học tiếng Anh" size="large" />
                                </Form.Item>

                                <Form.Item name="description" label="Mô tả">
                                    <TextArea rows={3} placeholder="Mô tả chức năng của chatbot..." showCount maxLength={500} />
                                </Form.Item>

                                <Form.Item name="icon" label="Icon (tùy chọn)">
                                    <Input placeholder="Emoji hoặc URL hình ảnh" />
                                </Form.Item>
                            </Card>

                            {/* SECTION 2: NGUỒN TRI THỨC */}
                            <Card
                                title="Nguồn tri thức"
                                style={{ marginBottom: 24, borderRadius: 8 }}
                                styles={{ header: { borderBottom: '2px solid #52c41a' } }}
                            >
                                <Form.Item name="dataset_ids" label="Datasets">
                                    <Select
                                        mode="multiple"
                                        placeholder="Chọn datasets làm knowledge base..."
                                        size="large"
                                    >
                                        {datasets.map(ds => (
                                            <Option key={ds.id} value={ds.id}>{ds.name}</Option>
                                        ))}
                                    </Select>
                                </Form.Item>
                                <Alert
                                    type="info"
                                    message="Chatbot chỉ trả lời dựa trên nội dung trong các datasets được chọn."
                                    style={{ marginTop: -8 }}
                                />
                            </Card>

                            {/* SECTION 3: RAG PIPELINE */}
                            <Card
                                title="RAG Pipeline"
                                style={{ marginBottom: 24, borderRadius: 8 }}
                                styles={{ header: { borderBottom: '2px solid #722ed1' } }}
                            >
                                {/* Step 1: Embedding */}
                                <div style={{ marginBottom: 32 }}>
                                    <div style={{
                                        display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16,
                                        padding: '8px 12px', background: '#f0f5ff', borderRadius: 6
                                    }}>
                                        <div style={{
                                            width: 28, height: 28, borderRadius: 6,
                                            background: '#1890ff', color: '#fff',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontWeight: 600, fontSize: 14
                                        }}>1</div>
                                        <span style={{ fontWeight: 500 }}>Embedding - Vector hóa câu hỏi</span>
                                    </div>

                                    {/* Hidden form field for default value */}
                                    <Form.Item name="embedding_model" hidden>
                                        <Input />
                                    </Form.Item>

                                    {/* Display current model (read-only) */}
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        padding: '12px 16px',
                                        background: '#fafafa',
                                        border: '1px solid #d9d9d9',
                                        borderRadius: 8
                                    }}>
                                        <div>
                                            <div style={{ fontWeight: 500, color: '#262626' }}>
                                                Vietnamese SBERT
                                            </div>
                                            <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
                                                Model: keepitreal/vietnamese-sbert • 768 dimensions
                                            </div>
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                            <Tag color="green">Mặc định</Tag>
                                            <Tag color="blue">Tối ưu cho tiếng Việt</Tag>
                                        </div>
                                    </div>
                                    <Alert
                                        type="info"
                                        message="Embedding model được cố định để đảm bảo tương thích với dữ liệu đã vector hóa trong Dataset."
                                        style={{ marginTop: 12, fontSize: 13 }}
                                        showIcon
                                    />
                                </div>

                                {/* Step 2: Retrieval */}
                                <div style={{ marginBottom: 32 }}>
                                    <div style={{
                                        display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16,
                                        padding: '8px 12px', background: '#e6fffb', borderRadius: 6
                                    }}>
                                        <div style={{
                                            width: 28, height: 28, borderRadius: 6,
                                            background: '#13c2c2', color: '#fff',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontWeight: 600, fontSize: 14
                                        }}>2</div>
                                        <span style={{ fontWeight: 500 }}>Retrieval - Tìm kiếm trong Vector DB</span>
                                    </div>

                                    <Form.Item name="search_mode" label="Chiến lược" style={{ marginBottom: 16 }}>
                                        <Radio.Group>
                                            <Radio.Button value="hybrid">Hybrid <Tag color="green">Khuyến nghị</Tag></Radio.Button>
                                            <Radio.Button value="vector">Vector Only</Radio.Button>
                                            <Radio.Button value="keyword">Keyword Only</Radio.Button>
                                        </Radio.Group>
                                    </Form.Item>

                                    <Row gutter={24}>
                                        <Col span={12}>
                                            <Form.Item
                                                name="top_k"
                                                label={<>Top K <Tooltip title="Số chunks lấy từ DB"><QuestionCircleOutlined style={{ color: '#999' }} /></Tooltip></>}
                                            >
                                                <InputNumber min={1} max={20} style={{ width: '100%' }} size="large" />
                                            </Form.Item>
                                        </Col>
                                        <Col span={12}>
                                            <Form.Item
                                                name="similarity_threshold"
                                                label={<>Ngưỡng tương đồng <Tooltip title="0.0 - 1.0"><QuestionCircleOutlined style={{ color: '#999' }} /></Tooltip></>}
                                            >
                                                <Slider min={0.1} max={0.9} step={0.05} marks={{ 0.3: '0.3', 0.5: '0.5', 0.7: '0.7' }} />
                                            </Form.Item>
                                        </Col>
                                    </Row>
                                </div>

                                {/* Step 3: Reranking */}
                                <div>
                                    <div style={{
                                        display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16,
                                        padding: '8px 12px', background: '#f9f0ff', borderRadius: 6
                                    }}>
                                        <div style={{
                                            width: 28, height: 28, borderRadius: 6,
                                            background: '#722ed1', color: '#fff',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontWeight: 600, fontSize: 14
                                        }}>3</div>
                                        <span style={{ fontWeight: 500 }}>Reranking - Sắp xếp lại kết quả</span>
                                    </div>

                                    <Row gutter={24}>
                                        <Col span={14}>
                                            <Form.Item name="reranker" label="Model Reranker" style={{ marginBottom: 0 }}>
                                                <Select size="large">
                                                    <Option value="None">
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                            <span>Không dùng Reranker</span>
                                                            <Tag color="cyan">Nhanh nhất</Tag>
                                                        </div>
                                                        <div style={{ fontSize: 11, color: '#888' }}>Chỉ dùng Vector similarity</div>
                                                    </Option>
                                                    <Option value="ms-marco-MiniLM-L-6-v2">
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                            <span>MiniLM-L6 (Siêu nhanh)</span>
                                                            <Tag color="green">~100-200ms</Tag>
                                                        </div>
                                                        <div style={{ fontSize: 11, color: '#888' }}>Tốt cho câu hỏi đơn giản</div>
                                                    </Option>
                                                    <Option value="ms-marco-MiniLM-L-12-v2">
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                            <span>MiniLM-L12 (Cân bằng)</span>
                                                            <Tag color="blue">~200-400ms</Tag>
                                                        </div>
                                                        <div style={{ fontSize: 11, color: '#888' }}>Cân bằng tốc độ và độ chính xác</div>
                                                    </Option>
                                                    <Option value="bge-reranker-v2-m3">
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                            <span>BGE-M3 (Chính xác nhất)</span>
                                                            <Tag color="purple">~2-8s</Tag>
                                                        </div>
                                                        <div style={{ fontSize: 11, color: '#888' }}>Tối ưu tiếng Việt, câu hỏi phức tạp</div>
                                                    </Option>
                                                </Select>
                                            </Form.Item>
                                        </Col>
                                        <Col span={10}>
                                            <Form.Item name="rerank_top_n" label="Giữ Top N" style={{ marginBottom: 0 }}>
                                                <InputNumber min={1} max={10} placeholder="Tất cả" style={{ width: '100%' }} size="large" />
                                            </Form.Item>
                                        </Col>
                                    </Row>
                                </div>
                            </Card>

                            {/* SECTION 4: LLM GENERATION */}
                            <Card
                                title="LLM Generation"
                                style={{ marginBottom: 24, borderRadius: 8 }}
                                styles={{ header: { borderBottom: '2px solid #fa8c16' } }}
                            >
                                <div style={{
                                    display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16,
                                    padding: '8px 12px', background: '#fff7e6', borderRadius: 6
                                }}>
                                    <div style={{
                                        width: 28, height: 28, borderRadius: 6,
                                        background: '#fa8c16', color: '#fff',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        fontWeight: 600, fontSize: 14
                                    }}>4</div>
                                    <span style={{ fontWeight: 500 }}>Sinh câu trả lời từ AI</span>
                                </div>

                                <Form.Item name="model" label="AI Model">
                                    <Select size="large">
                                        <Option value="models/gemini-2.5-flash">Gemini 2.5 Flash <Tag color="green">Nhanh</Tag></Option>
                                        <Option value="models/gemini-2.5-pro">Gemini 2.5 Pro <Tag color="purple">Thông minh</Tag></Option>
                                        <Option value="models/gemini-2.0-flash">Gemini 2.0 Flash</Option>
                                    </Select>
                                </Form.Item>

                                <Form.Item name="api_key" label="API Key riêng (tùy chọn)">
                                    <Input.Password placeholder="Để trống = dùng key hệ thống" size="large" />
                                </Form.Item>

                                <Row gutter={24}>
                                    <Col xs={24} sm={12}>
                                        <Form.Item name="temperature" label="Temperature" style={{ marginBottom: 16 }}>
                                            <Slider min={0} max={2} step={0.1} marks={{ 0: 'Chính xác', 1: '1.0', 2: 'Sáng tạo' }} style={{ margin: '10px 8px' }} />
                                        </Form.Item>
                                    </Col>
                                    <Col xs={24} sm={12}>
                                        <Form.Item name="max_tokens" label="Max Tokens" style={{ marginBottom: 16 }}>
                                            <InputNumber min={256} max={8192} step={256} style={{ width: '100%' }} size="large" />
                                        </Form.Item>
                                    </Col>
                                </Row>

                                <Form.Item name="system_prompt" label="System Prompt" style={{ marginBottom: 0 }}>
                                    <TextArea
                                        rows={4}
                                        placeholder="VD: Bạn là trợ lý AI của AIRC. Trả lời ngắn gọn, trích dẫn nguồn..."
                                        style={{ fontFamily: 'monospace' }}
                                    />
                                </Form.Item>
                            </Card>

                            {/* SECTION 5: NO CONTEXT BEHAVIOR */}
                            <Card
                                title="Xử lý khi không tìm thấy tài liệu"
                                style={{ marginBottom: 24, borderRadius: 8, background: '#fffbe6' }}
                                styles={{ header: { borderBottom: '2px solid #faad14' } }}
                            >
                                <Form.Item name="no_context_behavior" style={{ marginBottom: 16 }}>
                                    <Radio.Group style={{ width: '100%' }}>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                            <Radio value="reject" style={{ padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #d9d9d9' }}>
                                                <strong>Từ chối trả lời</strong> <Tag color="green">Khuyến nghị</Tag>
                                                <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>Thông báo không tìm thấy thông tin liên quan</div>
                                            </Radio>
                                            <Radio value="custom_message" style={{ padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #d9d9d9' }}>
                                                <strong>Thông báo tùy chỉnh</strong>
                                                <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>Hiển thị tin nhắn do bạn định nghĩa</div>
                                            </Radio>
                                            <Radio value="fallback_llm" style={{ padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #d9d9d9' }}>
                                                <strong>Dùng kiến thức LLM</strong> <Tag color="orange">Cẩn thận</Tag>
                                                <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>Cho phép AI trả lời từ kiến thức chung</div>
                                            </Radio>
                                        </div>
                                    </Radio.Group>
                                </Form.Item>

                                {noContextBehavior === 'custom_message' && (
                                    <Form.Item
                                        name="no_context_message"
                                        label="Nội dung thông báo"
                                        rules={[{ required: true, message: 'Vui lòng nhập' }]}
                                        style={{ marginBottom: 0 }}
                                    >
                                        <TextArea rows={2} placeholder="VD: Xin lỗi, tôi chưa có thông tin về vấn đề này..." />
                                    </Form.Item>
                                )}

                                {noContextBehavior === 'fallback_llm' && (
                                    <Alert type="warning" message="AI có thể trả lời không chính xác với ngữ cảnh tổ chức của bạn" showIcon />
                                )}
                            </Card>

                            {/* SECTION 6: PHÂN QUYỀN */}
                            <Card
                                title="Phân quyền truy cập"
                                style={{ marginBottom: 24, borderRadius: 8 }}
                                styles={{ header: { borderBottom: '2px solid #597ef7' } }}
                            >
                                <Row gutter={48}>
                                    <Col span={14}>
                                        <Form.Item
                                            name="allowed_roles"
                                            label="Vai trò được phép sử dụng"
                                            rules={[{ required: true, message: 'Chọn ít nhất 1 vai trò' }]}
                                        >
                                            <Select
                                                mode="multiple"
                                                size="large"
                                                placeholder="Chọn vai trò..."
                                                style={{ width: '100%' }}
                                            >
                                                <Option value="admin">Admin</Option>
                                                <Option
                                                    value="teacher"
                                                    disabled={rolesWithChatbot.includes('teacher')}
                                                >
                                                    Teacher {rolesWithChatbot.includes('teacher') && <LockOutlined style={{ marginLeft: 8 }} />}
                                                </Option>
                                                <Option
                                                    value="student"
                                                    disabled={rolesWithChatbot.includes('student')}
                                                >
                                                    Student {rolesWithChatbot.includes('student') && <LockOutlined style={{ marginLeft: 8 }} />}
                                                </Option>
                                            </Select>
                                        </Form.Item>
                                        {rolesWithChatbot.length > 0 && (
                                            <Alert
                                                type="info"
                                                message="Lưu ý: Mỗi role (trừ Admin) chỉ được gán 1 chatbot. Roles đã có chatbot khác sẽ bị khóa."
                                                showIcon
                                                style={{ marginTop: -16, marginBottom: 16 }}
                                            />
                                        )}
                                    </Col>
                                    <Col span={10}>
                                        <Form.Item name="visibility" label="Chế độ hiển thị">
                                            <Radio.Group>
                                                <Radio.Button value="public">Public</Radio.Button>
                                                <Radio.Button value="private">Private</Radio.Button>
                                            </Radio.Group>
                                        </Form.Item>
                                    </Col>
                                </Row>
                            </Card>

                            {/* SUBMIT BUTTONS */}
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 16, paddingTop: 8 }}>
                                <Button size="large" onClick={() => router.back()}>Hủy</Button>
                                <Button
                                    type="primary"
                                    size="large"
                                    htmlType="submit"
                                    icon={<SaveOutlined />}
                                    loading={saving}
                                    style={{ paddingLeft: 32, paddingRight: 32 }}
                                >
                                    Lưu thay đổi
                                </Button>
                            </div>
                        </Form>
                    </div>
                </div>
            </MainLayout>
        </AuthGuard>
    );
}
