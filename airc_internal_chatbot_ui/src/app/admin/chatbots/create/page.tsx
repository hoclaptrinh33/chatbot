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
    Typography,
    Breadcrumb,
    Radio,
    Slider,
    Row,
    Col,
    Tooltip,
    Alert,
    Tag
} from 'antd';
import { SaveOutlined, ArrowLeftOutlined, QuestionCircleOutlined, LockOutlined } from '@ant-design/icons';
import MainLayout from '@/components/Layout/MainLayout';
import AuthGuard from '@/components/Auth/AuthGuard';
import { chatbotService } from '@/services/chatbotService';
import datasetService from '@/services/datasetService';
import { ChatbotCreate } from '@/types/chatbot';
import { Dataset } from '@/core/entities/Dataset';
import { useRouter } from 'next/navigation';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

export default function CreateChatbotPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [datasets, setDatasets] = useState<Dataset[]>([]);
    const [rolesWithChatbot, setRolesWithChatbot] = useState<string[]>([]);
    const [form] = Form.useForm();

    const noContextBehavior = Form.useWatch('no_context_behavior', form);

    useEffect(() => {
        fetchDatasets();
        fetchRolesWithChatbot();
    }, []);

    const fetchDatasets = async () => {
        try {
            const data = await datasetService.getDatasets();
            setDatasets(data);
        } catch (error) {
            console.error("Failed to fetch datasets", error);
            message.error('Không thể tải danh sách datasets');
        }
    };

    const fetchRolesWithChatbot = async () => {
        try {
            const roles = await chatbotService.getRolesWithChatbot();
            setRolesWithChatbot(roles);
        } catch (error) {
            console.error("Failed to fetch roles with chatbot", error);
        }
    };

    const onFinish = async (values: Record<string, unknown>) => {
        console.log('Form values:', values);
        setLoading(true);
        try {
            // Build payload matching backend ChatbotCreate schema exactly
            const payload: ChatbotCreate = {
                name: values.name as string,
                description: (values.description as string) || undefined,
                icon: (values.icon as string) || undefined,
                visibility: (values.visibility as 'public' | 'private') || 'public',
                allowed_roles: (values.allowed_roles as string[]) || ['admin'],
                dataset_ids: (values.dataset_ids as string[]) || [],
                // Config object - Backend sẽ dùng default nếu không gửi field
                config: {
                    // Embedding (fixed)
                    embedding_model: 'vietnamese-sbert',
                    // Retrieval
                    search_mode: (values.search_mode as 'hybrid' | 'vector' | 'keyword') || 'hybrid',
                    top_k: (values.top_k as number) || 5,
                    similarity_threshold: (values.similarity_threshold as number) ?? 0.5,
                    // Reranking
                    reranker: (values.reranker as string) || 'Semantic',
                    rerank_top_n: (values.rerank_top_n as number) || undefined,
                    // LLM Generation
                    model: (values.model as string) || 'models/gemini-2.5-flash',
                    api_key: (values.api_key as string) || undefined,
                    temperature: (values.temperature as number) ?? 0.7,
                    max_tokens: (values.max_tokens as number) || 2048,
                    system_prompt: (values.system_prompt as string) || undefined,
                    // No context behavior
                    no_context_behavior: (values.no_context_behavior as 'reject' | 'fallback_llm' | 'custom_message') || 'reject',
                    no_context_message: (values.no_context_message as string) || undefined,
                }
            };

            console.log('Payload to send:', JSON.stringify(payload, null, 2));

            const result = await chatbotService.createChatbot(payload);
            console.log('Create result:', result);
            message.success('Tạo chatbot thành công!');
            router.push('/admin/chatbots');
        } catch (error: unknown) {
            console.error('Create chatbot error:', error);
            // Type-safe error handling
            if (error && typeof error === 'object' && 'response' in error) {
                const axiosError = error as { response?: { data?: { detail?: string }; status?: number } };
                console.error('Response status:', axiosError.response?.status);
                console.error('Response data:', axiosError.response?.data);
                message.error(axiosError.response?.data?.detail || 'Có lỗi xảy ra khi tạo chatbot');
            } else {
                message.error('Có lỗi xảy ra khi tạo chatbot');
            }
        } finally {
            setLoading(false);
        }
    };

    const onFinishFailed = (errorInfo: { values: unknown; errorFields: { name: (string | number)[]; errors: string[] }[]; outOfDate: boolean }) => {
        console.log('Form validation failed:', errorInfo);
        const firstError = errorInfo.errorFields[0];
        if (firstError) {
            message.error(`Vui lòng kiểm tra: ${firstError.errors[0]}`);
            // Scroll to the first error field
            form.scrollToField(firstError.name);
        }
    };

    return (
        <AuthGuard>
            <MainLayout>
                <div style={{ background: '#f5f5f5', minHeight: '100vh', margin: -24, padding: 32 }}>
                    {/* Header */}
                    <div style={{ maxWidth: 800, margin: '0 auto 32px' }}>
                        <Breadcrumb
                            items={[
                                { title: 'Dashboard', href: '/dashboard' },
                                { title: 'Admin' },
                                { title: 'Chatbots', href: '/admin/chatbots' },
                                { title: 'Tạo mới' },
                            ]}
                        />
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 16 }}>
                            <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()} type="text" />
                            <Title level={3} style={{ margin: 0 }}>Tạo Chatbot Mới</Title>
                        </div>
                    </div>

                    {/* RAG Pipeline Overview */}
                    <div style={{ maxWidth: 800, margin: '0 auto 24px' }}>
                        <Card style={{ borderRadius: 8 }}>
                            <div style={{ textAlign: 'center', marginBottom: 16 }}>
                                <span style={{ fontWeight: 600, fontSize: 14, color: '#666' }}>RAG Pipeline Flow</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                {[
                                    { step: '1', label: 'Query', desc: 'Câu hỏi', color: '#1890ff' },
                                    { step: '2', label: 'Embedding', desc: 'Vector hóa', color: '#1890ff' },
                                    { step: '3', label: 'Retrieval', desc: 'Tìm kiếm', color: '#13c2c2' },
                                    { step: '4', label: 'Reranking', desc: 'Sắp xếp', color: '#722ed1' },
                                    { step: '5', label: 'Generation', desc: 'Trả lời', color: '#fa8c16' },
                                ].map((item, idx) => (
                                    <React.Fragment key={item.step}>
                                        <div style={{ textAlign: 'center', flex: '0 0 auto' }}>
                                            <div style={{
                                                width: 36, height: 36, borderRadius: '50%',
                                                background: item.color, color: '#fff',
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                fontWeight: 600, fontSize: 14, margin: '0 auto 8px'
                                            }}>{item.step}</div>
                                            <div style={{ fontWeight: 500, fontSize: 13 }}>{item.label}</div>
                                            <div style={{ fontSize: 11, color: '#999' }}>{item.desc}</div>
                                        </div>
                                        {idx < 4 && (
                                            <div style={{ flex: 1, height: 2, background: '#e8e8e8', margin: '0 8px', marginBottom: 24 }} />
                                        )}
                                    </React.Fragment>
                                ))}
                            </div>
                        </Card>
                    </div>

                    <div style={{ maxWidth: 800, margin: '0 auto' }}>
                        <Form
                            form={form}
                            layout="vertical"
                            onFinish={onFinish}
                            onFinishFailed={onFinishFailed}
                            scrollToFirstError
                            initialValues={{
                                visibility: 'public',
                                allowed_roles: ['admin'], // Mặc định chỉ admin, các role khác phải chọn thủ công
                                embedding_model: 'vietnamese-sbert',
                                search_mode: 'hybrid',
                                top_k: 5,
                                similarity_threshold: 0.5,
                                reranker: 'ms-marco-MiniLM-L-6-v2',
                                model: 'models/gemini-2.5-flash',
                                temperature: 0.7,
                                max_tokens: 2048,
                                no_context_behavior: 'reject',
                            }}
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
                                                message="Lưu ý: Mỗi role (trừ Admin) chỉ được gán 1 chatbot. Roles đã có chatbot sẽ bị khóa."
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
                                    loading={loading}
                                    style={{ paddingLeft: 32, paddingRight: 32 }}
                                >
                                    Tạo Chatbot
                                </Button>
                            </div>
                        </Form>
                    </div>
                </div>
            </MainLayout>
        </AuthGuard>
    );
}
