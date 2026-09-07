'use client';

import React from 'react';
import { AutoComplete, Spin } from 'antd';

interface LlmModelSelectProps {
    models: string[];
    loading?: boolean;
    value?: string;
    onChange?: (value: string) => void;
    placeholder?: string;
    size?: 'large' | 'middle' | 'small';
    disabled?: boolean;
}

export default function LlmModelSelect({
    models,
    loading = false,
    value,
    onChange,
    placeholder = 'Chọn từ danh sách hoặc tự nhập tên model',
    size = 'large',
    disabled,
}: LlmModelSelectProps) {
    const options = models.map((model) => ({ value: model, label: model }));
    if (value && !models.includes(value)) {
        options.unshift({ value, label: value });
    }

    return (
        <AutoComplete
            size={size}
            value={value}
            onChange={onChange}
            options={options}
            placeholder={placeholder}
            disabled={disabled}
            filterOption={(inputValue, option) =>
                String(option?.value || '').toUpperCase().includes(inputValue.toUpperCase())
            }
            notFoundContent={loading ? <Spin size="small" /> : 'Không có model từ endpoint'}
        />
    );
}
