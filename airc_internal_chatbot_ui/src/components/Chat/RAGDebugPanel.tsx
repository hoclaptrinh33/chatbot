'use client';

import React, { useState } from 'react';
import { Card, Table, Tag, Tooltip, Typography, Row, Col, Statistic, Divider } from 'antd';
import {
    ClockCircleOutlined,
    ThunderboltOutlined,
    DatabaseOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    InfoCircleOutlined,
    BarChartOutlined
} from '@ant-design/icons';

const { Text, Title } = Typography;

export interface RAGDebugMetrics {
    total_time_ms: number;
    embedding_time_ms: number;
    retrieval_time_ms: number;
    rerank_time_ms: number;
    llm_time_ms: number;
    cache_hit: boolean;
    chunks_found: number;
    chunks_after_rerank: number;
    avg_similarity_score: number;
    top_similarity_score: number;
    datasets_searched: number;
    model_used: string | null;
    reranker_used: string | null;
    no_context: boolean;
}

interface RAGDebugPanelProps {
    metrics: RAGDebugMetrics | null;
}

// Format time display
const formatTime = (ms: number): string => {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
};

// Get performance rating
const getPerformanceRating = (totalMs: number): { color: string; label: string } => {
    if (totalMs < 1000) return { color: '#52c41a', label: 'Xuất sắc' };
    if (totalMs < 2000) return { color: '#1890ff', label: 'Tốt' };
    if (totalMs < 4000) return { color: '#faad14', label: 'Trung bình' };
    return { color: '#ff4d4f', label: 'Chậm' };
};

// Get accuracy rating
const getAccuracyRating = (score: number): { color: string; label: string } => {
    if (score >= 0.8) return { color: '#52c41a', label: 'Rất cao' };
    if (score >= 0.6) return { color: '#1890ff', label: 'Cao' };
    if (score >= 0.4) return { color: '#faad14', label: 'Trung bình' };
    if (score > 0) return { color: '#ff4d4f', label: 'Thấp' };
    return { color: '#d9d9d9', label: 'N/A' };
};

export default function RAGDebugPanel({ metrics }: RAGDebugPanelProps) {
    const [expanded, setExpanded] = useState(false);

    if (!metrics) return null;

    const perfRating = getPerformanceRating(metrics.total_time_ms);
    const accuracyRating = getAccuracyRating(metrics.top_similarity_score);

    // Pipeline stages data
    const pipelineData = [
        {
            key: 'embedding',
            stage: '1. Embedding',
            description: 'Chuyển câu hỏi thành vector',
            time: metrics.embedding_time_ms,
            percentage: ((metrics.embedding_time_ms / metrics.total_time_ms) * 100).toFixed(1),
            status: metrics.embedding_time_ms < 100 ? 'success' : metrics.embedding_time_ms < 300 ? 'warning' : 'error'
        },
        {
            key: 'retrieval',
            stage: '2. Retrieval',
            description: 'Tìm kiếm chunks từ vector DB',
            time: metrics.retrieval_time_ms,
            percentage: ((metrics.retrieval_time_ms / metrics.total_time_ms) * 100).toFixed(1),
            status: metrics.retrieval_time_ms < 500 ? 'success' : metrics.retrieval_time_ms < 1000 ? 'warning' : 'error'
        },
        {
            key: 'rerank',
            stage: '3. Rerank',
            description: 'Sắp xếp lại độ liên quan',
            time: metrics.rerank_time_ms,
            percentage: ((metrics.rerank_time_ms / metrics.total_time_ms) * 100).toFixed(1),
            status: metrics.rerank_time_ms < 200 ? 'success' : metrics.rerank_time_ms < 500 ? 'warning' : 'error'
        },
        {
            key: 'llm',
            stage: '4. LLM Generation',
            description: 'Sinh câu trả lời từ AI',
            time: metrics.llm_time_ms,
            percentage: ((metrics.llm_time_ms / metrics.total_time_ms) * 100).toFixed(1),
            status: metrics.llm_time_ms < 2000 ? 'success' : metrics.llm_time_ms < 4000 ? 'warning' : 'error'
        }
    ];

    const columns = [
        {
            title: 'Giai đoạn',
            dataIndex: 'stage',
            key: 'stage',
            render: (text: string, record: typeof pipelineData[0]) => (
                <Tooltip title={record.description}>
                    <span style={{ fontWeight: 500 }}>{text}</span>
                </Tooltip>
            )
        },
        {
            title: 'Thời gian',
            dataIndex: 'time',
            key: 'time',
            align: 'right' as const,
            render: (time: number) => (
                <Text strong>{formatTime(time)}</Text>
            )
        },
        {
            title: 'Tỷ lệ',
            dataIndex: 'percentage',
            key: 'percentage',
            align: 'right' as const,
            render: (pct: string, record: typeof pipelineData[0]) => (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end' }}>
                    <div style={{
                        width: 60,
                        height: 6,
                        background: '#f0f0f0',
                        borderRadius: 3,
                        overflow: 'hidden'
                    }}>
                        <div style={{
                            width: `${pct}%`,
                            height: '100%',
                            background: record.status === 'success' ? '#52c41a' : record.status === 'warning' ? '#faad14' : '#ff4d4f',
                            borderRadius: 3
                        }} />
                    </div>
                    <Text type="secondary" style={{ fontSize: 12, minWidth: 40 }}>{pct}%</Text>
                </div>
            )
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            key: 'status',
            align: 'center' as const,
            render: (status: string) => (
                status === 'success' ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                    status === 'warning' ? <ClockCircleOutlined style={{ color: '#faad14' }} /> :
                        <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
            )
        }
    ];

    return (
        <Card
            size="small"
            style={{
                marginTop: 16,
                borderRadius: 8,
                border: '1px solid #e8e8e8',
                background: '#fafafa'
            }}
            styles={{
                body: { padding: expanded ? 16 : 12 }
            }}
        >
            {/* Header - Always visible */}
            <div
                onClick={() => setExpanded(!expanded)}
                style={{
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <BarChartOutlined style={{ fontSize: 16, color: '#1890ff' }} />
                    <Text strong style={{ color: '#333' }}>RAG Performance Debug</Text>
                    {metrics.cache_hit && (
                        <Tag color="green" icon={<ThunderboltOutlined />}>CACHE HIT</Tag>
                    )}
                    {metrics.no_context && (
                        <Tag color="orange">NO CONTEXT</Tag>
                    )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <Tooltip title="Thời gian tổng">
                        <Tag color={perfRating.color} style={{ margin: 0 }}>
                            <ClockCircleOutlined /> {formatTime(metrics.total_time_ms)}
                        </Tag>
                    </Tooltip>
                    <Tooltip title="Độ chính xác cao nhất">
                        <Tag color={accuracyRating.color} style={{ margin: 0 }}>
                            Score: {(metrics.top_similarity_score * 100).toFixed(0)}%
                        </Tag>
                    </Tooltip>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                        {expanded ? '▲ Thu gọn' : '▼ Chi tiết'}
                    </Text>
                </div>
            </div>

            {/* Expanded Content */}
            {expanded && (
                <>
                    <Divider style={{ margin: '12px 0' }} />

                    {/* Summary Statistics */}
                    <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={6}>
                            <Statistic
                                title={<Text type="secondary" style={{ fontSize: 12 }}>Tổng thời gian</Text>}
                                value={metrics.total_time_ms}
                                suffix="ms"
                                valueStyle={{ color: perfRating.color, fontSize: 20 }}
                                prefix={<ClockCircleOutlined />}
                            />
                            <Tag color={perfRating.color} style={{ marginTop: 4 }}>{perfRating.label}</Tag>
                        </Col>
                        <Col span={6}>
                            <Statistic
                                title={<Text type="secondary" style={{ fontSize: 12 }}>Chunks tìm thấy</Text>}
                                value={metrics.chunks_found}
                                valueStyle={{ fontSize: 20 }}
                                prefix={<DatabaseOutlined />}
                            />
                            <Text type="secondary" style={{ fontSize: 11 }}>
                                {metrics.datasets_searched} dataset(s)
                            </Text>
                        </Col>
                        <Col span={6}>
                            <Statistic
                                title={<Text type="secondary" style={{ fontSize: 12 }}>Top Similarity</Text>}
                                value={(metrics.top_similarity_score * 100).toFixed(1)}
                                suffix="%"
                                valueStyle={{ color: accuracyRating.color, fontSize: 20 }}
                            />
                            <Tag color={accuracyRating.color} style={{ marginTop: 4 }}>{accuracyRating.label}</Tag>
                        </Col>
                        <Col span={6}>
                            <Statistic
                                title={<Text type="secondary" style={{ fontSize: 12 }}>Avg Similarity</Text>}
                                value={(metrics.avg_similarity_score * 100).toFixed(1)}
                                suffix="%"
                                valueStyle={{ fontSize: 20 }}
                            />
                        </Col>
                    </Row>

                    {/* Pipeline Breakdown Table */}
                    <Title level={5} style={{ marginBottom: 8, fontSize: 13 }}>
                        <InfoCircleOutlined /> Chi tiết Pipeline RAG
                    </Title>
                    <Table
                        dataSource={pipelineData}
                        columns={columns}
                        pagination={false}
                        size="small"
                        style={{ marginBottom: 12 }}
                    />

                    {/* Model Info */}
                    <div style={{
                        display: 'flex',
                        gap: 8,
                        flexWrap: 'wrap',
                        padding: '8px 0',
                        borderTop: '1px solid #f0f0f0'
                    }}>
                        {metrics.model_used && (
                            <Tag color="blue">Model: {metrics.model_used}</Tag>
                        )}
                        {metrics.reranker_used && (
                            <Tag color="purple">Reranker: {metrics.reranker_used}</Tag>
                        )}
                        <Tag color="default">Embedding: vietnamese-sbert</Tag>
                    </div>
                </>
            )}
        </Card>
    );
}
