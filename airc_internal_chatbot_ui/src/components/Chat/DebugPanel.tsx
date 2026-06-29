'use client';

import React, { useState } from 'react';
import { Collapse, Tag, Tooltip } from 'antd';
import {
    ClockCircleOutlined,
    DatabaseOutlined,
    ThunderboltOutlined,
    CheckCircleOutlined,
    RobotOutlined
} from '@ant-design/icons';

export interface DebugMetrics {
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

interface DebugPanelProps {
    metrics: DebugMetrics | null;
    className?: string;
}

// Helper to format time
const formatTime = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
};

// Helper to get score color
const getScoreColor = (score: number): string => {
    if (score >= 0.8) return '#52c41a';
    if (score >= 0.6) return '#1890ff';
    if (score >= 0.4) return '#faad14';
    return '#ff4d4f';
};

// Helper to get score label
const getScoreLabel = (score: number): string => {
    if (score >= 0.8) return 'Rất tốt';
    if (score >= 0.6) return 'Tốt';
    if (score >= 0.4) return 'Trung bình';
    return 'Thấp';
};

export default function DebugPanel({ metrics, className = '' }: DebugPanelProps) {
    const [expanded, setExpanded] = useState(false);

    if (!metrics) return null;

    // Calculate time percentages for visualization
    const totalNonZero = metrics.total_time_ms || 1;
    const timeBreakdown = [
        { label: 'Embedding', time: metrics.embedding_time_ms, color: '#1890ff' },
        { label: 'Retrieval', time: metrics.retrieval_time_ms, color: '#13c2c2' },
        { label: 'Reranking', time: metrics.rerank_time_ms, color: '#722ed1' },
        { label: 'LLM', time: metrics.llm_time_ms, color: '#fa8c16' },
    ];

    return (
        <div className={`${className}`} style={{ marginTop: 8 }}>
            <Collapse
                size="small"
                activeKey={expanded ? ['1'] : []}
                onChange={() => setExpanded(!expanded)}
                style={{ background: '#fafafa', border: '1px solid #f0f0f0' }}
                items={[{
                    key: '1',
                    label: (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 12 }}>
                            <span style={{ fontWeight: 500, color: '#666' }}>Debug Info</span>
                            <Tag color={metrics.cache_hit ? 'green' : 'default'} style={{ margin: 0 }}>
                                {metrics.cache_hit ? 'Cache Hit' : 'Fresh'}
                            </Tag>
                            <span style={{ color: '#999' }}>
                                <ClockCircleOutlined /> {formatTime(metrics.total_time_ms)}
                            </span>
                            {metrics.chunks_found > 0 && (
                                <span style={{ color: '#999' }}>
                                    <DatabaseOutlined /> {metrics.chunks_found} chunks
                                </span>
                            )}
                            {metrics.top_similarity_score > 0 && (
                                <span style={{ color: getScoreColor(metrics.top_similarity_score) }}>
                                    Score: {(metrics.top_similarity_score * 100).toFixed(0)}%
                                </span>
                            )}
                        </div>
                    ),
                    children: (
                        <div style={{ fontSize: 12 }}>
                            {/* Time Breakdown */}
                            <div style={{ marginBottom: 16 }}>
                                <div style={{ fontWeight: 500, marginBottom: 8, color: '#333' }}>
                                    Thời gian xử lý
                                </div>
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                    <tbody>
                                        {timeBreakdown.map(item => (
                                            <tr key={item.label}>
                                                <td style={{ padding: '4px 0', width: 90, color: '#666' }}>
                                                    {item.label}
                                                </td>
                                                <td style={{ padding: '4px 8px' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                        <div style={{
                                                            flex: 1,
                                                            height: 8,
                                                            background: '#f0f0f0',
                                                            borderRadius: 4,
                                                            overflow: 'hidden'
                                                        }}>
                                                            <div style={{
                                                                width: `${Math.min((item.time / totalNonZero) * 100, 100)}%`,
                                                                height: '100%',
                                                                background: item.color,
                                                                borderRadius: 4,
                                                                transition: 'width 0.3s'
                                                            }} />
                                                        </div>
                                                        <span style={{
                                                            minWidth: 60,
                                                            textAlign: 'right',
                                                            fontFamily: 'monospace',
                                                            color: item.time > 1000 ? '#fa8c16' : '#666'
                                                        }}>
                                                            {formatTime(item.time)}
                                                        </span>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                        <tr style={{ borderTop: '1px solid #f0f0f0' }}>
                                            <td style={{ padding: '8px 0', fontWeight: 600, color: '#333' }}>
                                                Tổng
                                            </td>
                                            <td style={{ padding: '8px 8px', textAlign: 'right' }}>
                                                <span style={{
                                                    fontWeight: 600,
                                                    fontFamily: 'monospace',
                                                    color: metrics.total_time_ms > 5000 ? '#ff4d4f' :
                                                        metrics.total_time_ms > 3000 ? '#fa8c16' : '#52c41a'
                                                }}>
                                                    {formatTime(metrics.total_time_ms)}
                                                </span>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            {/* Retrieval Stats */}
                            <div style={{ marginBottom: 16 }}>
                                <div style={{ fontWeight: 500, marginBottom: 8, color: '#333' }}>
                                    Retrieval
                                </div>
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                    <tbody>
                                        <tr>
                                            <td style={{ padding: '4px 0', color: '#666' }}>Datasets tìm kiếm</td>
                                            <td style={{ padding: '4px 0', textAlign: 'right', fontFamily: 'monospace' }}>
                                                {metrics.datasets_searched}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style={{ padding: '4px 0', color: '#666' }}>Chunks tìm thấy</td>
                                            <td style={{ padding: '4px 0', textAlign: 'right', fontFamily: 'monospace' }}>
                                                {metrics.chunks_found}
                                                {metrics.no_context && (
                                                    <Tag color="warning" style={{ marginLeft: 8 }}>No Context</Tag>
                                                )}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style={{ padding: '4px 0', color: '#666' }}>Top Similarity</td>
                                            <td style={{ padding: '4px 0', textAlign: 'right' }}>
                                                <Tooltip title={getScoreLabel(metrics.top_similarity_score)}>
                                                    <span style={{
                                                        fontFamily: 'monospace',
                                                        color: getScoreColor(metrics.top_similarity_score),
                                                        fontWeight: 600
                                                    }}>
                                                        {(metrics.top_similarity_score * 100).toFixed(1)}%
                                                    </span>
                                                </Tooltip>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style={{ padding: '4px 0', color: '#666' }}>Avg Similarity</td>
                                            <td style={{ padding: '4px 0', textAlign: 'right' }}>
                                                <span style={{
                                                    fontFamily: 'monospace',
                                                    color: getScoreColor(metrics.avg_similarity_score)
                                                }}>
                                                    {(metrics.avg_similarity_score * 100).toFixed(1)}%
                                                </span>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            {/* Model Info */}
                            <div>
                                <div style={{ fontWeight: 500, marginBottom: 8, color: '#333' }}>
                                    Model
                                </div>
                                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                    {metrics.model_used && (
                                        <Tag icon={<RobotOutlined />} color="blue">
                                            {metrics.model_used.replace('models/', '')}
                                        </Tag>
                                    )}
                                    {metrics.reranker_used && metrics.reranker_used !== 'None' && (
                                        <Tag icon={<ThunderboltOutlined />} color="purple">
                                            Reranker: {metrics.reranker_used}
                                        </Tag>
                                    )}
                                    {metrics.cache_hit && (
                                        <Tag icon={<CheckCircleOutlined />} color="green">
                                            Cached Response
                                        </Tag>
                                    )}
                                </div>
                            </div>
                        </div>
                    )
                }]}
            />
        </div>
    );
}
