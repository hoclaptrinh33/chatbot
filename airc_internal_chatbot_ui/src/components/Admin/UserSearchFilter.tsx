import React from 'react';
import { Input, Select, Button, Row, Col } from 'antd';
import { SearchOutlined, ClearOutlined } from '@ant-design/icons';

interface UserSearchFilterProps {
    searchQuery: string;
    selectedRole: string;
    onSearchChange: (query: string) => void;
    onRoleChange: (role: string) => void;
    onReset: () => void;
    loading?: boolean;
    resultCount?: number;
}

/**
 * Component tìm kiếm và lọc users
 * 
 * Features:
 * - Input tìm kiếm theo tên/email
 * - Select lọc theo role
 * - Button reset filters
 * - Hiển thị số kết quả
 */
const UserSearchFilter: React.FC<UserSearchFilterProps> = ({
    searchQuery,
    selectedRole,
    onSearchChange,
    onRoleChange,
    onReset,
    loading = false,
    resultCount = 0,
}) => {
    const roleOptions = [
        { label: 'Admin', value: 'admin' },
        { label: 'Employee', value: 'employee' },
        { label: 'Intern/Guest', value: 'intern_guest' },
    ];

    return (
        <>
            {/* Search and Filter Bar */}
            <Row gutter={[16, 16]} className="mb-6">
                <Col xs={24} sm={12} md={10}>
                    <Input
                        placeholder="Tim kiem theo ten hoac email..."
                        prefix={<SearchOutlined />}
                        value={searchQuery}
                        onChange={(e) => onSearchChange(e.target.value)}
                        allowClear
                        disabled={loading}
                    />
                </Col>
                <Col xs={24} sm={12} md={8}>
                    <Select
                        placeholder="Loc theo vai tro"
                        value={selectedRole}
                        onChange={onRoleChange}
                        style={{ width: '100%' }}
                        allowClear
                        options={roleOptions}
                        disabled={loading}
                    />
                </Col>
                <Col xs={24} sm={24} md={6} className="flex justify-end">
                    <Button
                        icon={<ClearOutlined />}
                        onClick={onReset}
                        className="w-full"
                        disabled={loading}
                    >
                        
                    </Button>
                </Col>
            </Row>

            {/* Results Count */}
            <div className="mb-4 text-gray-500">
                Tong cong: <span className="font-semibold">{resultCount}</span> users
                {searchQuery && <span> (Tim kiem: "{searchQuery}")</span>}
                {selectedRole && <span> (Vai tro: {selectedRole.toUpperCase()})</span>}
            </div>
        </>
    );
};

export default UserSearchFilter;
