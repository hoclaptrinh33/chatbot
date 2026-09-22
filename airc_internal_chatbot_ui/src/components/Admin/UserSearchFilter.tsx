import React from 'react';
import { Input, Select, Button, Row, Col } from 'antd';
import { SearchOutlined, ClearOutlined } from '@ant-design/icons';

interface UserSearchFilterProps {
    searchQuery: string;
    selectedRole: string;
    selectedDepartment: string;
    onSearchChange: (query: string) => void;
    onRoleChange: (role: string) => void;
    onDepartmentChange: (department: string) => void;
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
    selectedDepartment,
    onSearchChange,
    onRoleChange,
    onDepartmentChange,
    onReset,
    loading = false,
    resultCount = 0,
}) => {
    const roleOptions = [
        { label: 'Quản trị viên', value: 'admin' },
        { label: 'Nhân viên', value: 'employee' },
        { label: 'Thực tập sinh/Khách', value: 'intern_guest' },
    ];

    return (
        <>
            {/* Search and Filter Bar */}
            <Row gutter={[16, 16]} className="mb-2">
                <Col xs={24} sm={12} md={8}>
                    <Input
                        placeholder="Tìm kiếm theo tên, email hoặc phòng ban..."
                        prefix={<SearchOutlined />}
                        value={searchQuery}
                        onChange={(e) => onSearchChange(e.target.value)}
                        allowClear
                        disabled={loading}
                    />
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Select
                        placeholder="Lọc theo vai trò"
                        value={selectedRole}
                        onChange={onRoleChange}
                        style={{ width: '100%' }}
                        allowClear
                        options={roleOptions}
                        disabled={loading}
                    />
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Input
                        placeholder="Lọc theo phòng ban/đơn vị"
                        value={selectedDepartment}
                        onChange={(e) => onDepartmentChange(e.target.value)}
                        allowClear
                        disabled={loading}
                    />
                </Col>
                <Col xs={24} sm={24} md={4} className="flex justify-end">
                    <Button
                        icon={<ClearOutlined />}
                        onClick={onReset}
                        className="w-full"
                        disabled={loading}
                    >
                        Xóa bộ lọc
                    </Button>
                </Col>
            </Row>

            {/* Results Count */}
            <div className=" text-gray-500">
                Tổng cộng: <span className="font-semibold">{resultCount}</span> người dùng
                {searchQuery && <span> (Tìm kiếm: "{searchQuery}")</span>}
                {selectedRole && <span> (Vai trò: {selectedRole.toUpperCase()})</span>}
                {selectedDepartment && <span> (Phòng ban: {selectedDepartment})</span>}
            </div>
        </>
    );
};

export default UserSearchFilter;
