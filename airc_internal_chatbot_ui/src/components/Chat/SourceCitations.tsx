'use client';

import React, { useState } from 'react';
import { Button, Collapse, Drawer, Tag, Tooltip, Typography, message } from 'antd';
import { FileTextOutlined, LinkOutlined } from '@ant-design/icons';
import { DatasetSearchResult } from '@/core/entities/Chat';
import { coreClient } from '@/infrastructure/http/core.client';

const { Text, Paragraph } = Typography;

interface SourceCitationsProps {
    sources?: DatasetSearchResult[];
}

function snippet(text?: string, max = 220): string {
    if (!text) return '';
    const compact = text.replace(/\s+/g, ' ').trim();
    return compact.length > max ? `${compact.slice(0, max)}…` : compact;
}

async function openSourceFile(fileId: string, fileName?: string) {
    try {
        const response = await coreClient.get(`/files/${fileId}/view`, {
            responseType: 'blob',
        });
        const blob = new Blob([response.data], {
            type: response.headers['content-type'] || 'application/octet-stream',
        });
        const url = URL.createObjectURL(blob);
        const opened = window.open(url, '_blank', 'noopener,noreferrer');
        if (!opened) {
            const link = document.createElement('a');
            link.href = url;
            link.download = fileName || 'document';
            link.click();
        }
        setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
        console.error(err);
        message.error('Không mở được tài liệu nguồn. Kiểm tra quyền truy cập.');
    }
}

export default function SourceCitations({ sources }: SourceCitationsProps) {
    const [opening, setOpening] = useState<string | null>(null);
    const [preview, setPreview] = useState<{ title: string; text: string; fileId?: string } | null>(null);
    const items = (sources || []).flatMap((group) =>
        (group.results || []).map((result, idx) => ({
            key: `${group.dataset_id}-${result.file_id}-${result.chunk_index}-${idx}`,
            group,
            result,
        }))
    );

    if (items.length === 0) return null;

    return (
        <div className="mt-2 w-full max-w-xl">
            <Collapse
                size="small"
                ghost
                items={[
                    {
                        key: 'sources',
                        label: (
                            <Text type="secondary" className="text-xs">
                                Nguồn tham chiếu ({items.length})
                            </Text>
                        ),
                        children: (
                            <div className="flex flex-col gap-2">
                                {items.map(({ key, group, result }) => (
                                    <div
                                        key={key}
                                        className="rounded-lg border border-gray-200 bg-white px-3 py-2 cursor-pointer hover:border-red-300"
                                        onClick={() => setPreview({
                                            title: result.file_name || group.dataset_name || 'Tài liệu',
                                            text: result.text || '',
                                            fileId: result.file_id,
                                        })}
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="min-w-0">
                                                <div className="flex items-center gap-1.5 flex-wrap">
                                                    <FileTextOutlined className="text-red-600" />
                                                    <Text strong className="text-xs truncate">
                                                        {result.file_name || 'Tài liệu'}
                                                    </Text>
                                                    {group.dataset_name && (
                                                        <Tag className="m-0 text-[10px]">{group.dataset_name}</Tag>
                                                    )}
                                                    {typeof result.score === 'number' && (
                                                        <Tag color="blue" className="m-0 text-[10px]">
                                                            {(result.score * 100).toFixed(0)}%
                                                        </Tag>
                                                    )}
                                                </div>
                                                <Paragraph className="!mb-0 !mt-1 text-[11px] text-gray-500">
                                                    {snippet(result.text)}
                                                </Paragraph>
                                            </div>
                                            {result.file_id && (
                                                <Tooltip title="Mở tài liệu gốc">
                                                    <Button
                                                        size="small"
                                                        type="text"
                                                        icon={<LinkOutlined />}
                                                        loading={opening === result.file_id}
                                                        onClick={async (event) => {
                                                            event.stopPropagation();
                                                            setOpening(result.file_id);
                                                            await openSourceFile(result.file_id, result.file_name);
                                                            setOpening(null);
                                                        }}
                                                    />
                                                </Tooltip>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ),
                    },
                ]}
            />
            <Drawer
                title={preview?.title || 'Đoạn nguồn'}
                open={!!preview}
                onClose={() => setPreview(null)}
                width={480}
            >
                {preview && (
                    <div className="space-y-3">
                        <div className="text-sm leading-6 bg-amber-50 border border-amber-200 rounded-md p-3">
                            <mark className="bg-amber-200">{preview.text}</mark>
                        </div>
                        {preview.fileId && (
                            <Button
                                type="primary"
                                loading={opening === preview.fileId}
                                onClick={async () => {
                                    setOpening(preview.fileId || null);
                                    await openSourceFile(preview.fileId as string, preview.title);
                                    setOpening(null);
                                }}
                            >
                                Mở tài liệu gốc
                            </Button>
                        )}
                    </div>
                )}
            </Drawer>
        </div>
    );
}
