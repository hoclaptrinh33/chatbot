import React, { useMemo } from 'react';
import { Table, Checkbox, Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Role, Permission } from '@/services/rbacService';

interface PermissionMatrixProps {
    roles: Role[];
    permissions: Permission[];
    matrix: Record<string, string[]>; // role_code -> permission_codes
    loading?: boolean;
    onChange?: (roleCode: string, permissionCode: string, checked: boolean) => void;
    readOnly?: boolean;
    targetRole?: Role | null; // If provided, highlights this role's column
}

interface MatrixRow {
    key: string;
    resource: string;
    permission: Permission;
    [roleCode: string]: boolean | string | Permission;
}

const PermissionMatrix: React.FC<PermissionMatrixProps> = ({
    roles,
    permissions,
    matrix,
    loading = false,
    onChange,
    readOnly = false,
    targetRole
}) => {
    // Filter roles if targetRole is provided
    const displayRoles = useMemo(() => {
        if (targetRole) {
            // Only show the target role
            return roles.filter(r => r.code === targetRole.code);
        }
        return roles;
    }, [roles, targetRole]);

    // Group permissions by resource
    const rows = useMemo(() => {
        return permissions.map(perm => ({
            key: perm.id || perm._id!,
            resource: perm.resource,
            permission: perm,
            ...displayRoles.reduce((acc, role) => ({
                ...acc,
                [role.code]: (matrix[role.code] || []).includes(perm.code)
            }), {})
        }));
    }, [permissions, displayRoles, matrix]);

    const columns: ColumnsType<MatrixRow> = [
        {
            title: 'Resource',
            dataIndex: 'resource',
            key: 'resource',
            width: 120,
            fixed: 'left',
            render: (text: string, record: MatrixRow, index: number) => {
                const obj = {
                    children: <Tag color="blue">{text.toUpperCase()}</Tag>,
                    props: { rowSpan: 1 }
                };

                // RowSpan logic for grouping
                if (index > 0 && permissions[index].resource === permissions[index - 1].resource) {
                    obj.props.rowSpan = 0;
                } else {
                    let count = 0;
                    for (let i = index; i < permissions.length; i++) {
                        if (permissions[i].resource === permissions[index].resource) {
                            count++;
                        } else {
                            break;
                        }
                    }
                    obj.props.rowSpan = count;
                }
                return obj;
            }
        },
        {
            title: 'Permission',
            dataIndex: 'permission',
            key: 'permission',
            width: 200,
            fixed: 'left',
            render: (perm: Permission) => (
                <Tooltip title={perm.description}>
                    <span className="font-medium">{perm.name}</span>
                    <div className="text-xs text-gray-400">{perm.code}</div>
                </Tooltip>
            )
        },
        ...displayRoles.map(role => ({
            title: (
                <div className={`text-center ${targetRole?.code === role.code ? 'text-blue-600 font-bold' : ''}`}>
                    {role.name}
                    {role.is_system && <Tag className="ml-1" color="orange">SYS</Tag>}
                </div>
            ),
            dataIndex: role.code,
            key: role.code,
            width: 120,
            align: 'center' as const,
            render: (checked: boolean, record: MatrixRow) => (
                <Checkbox
                    checked={checked}
                    disabled={!!(readOnly || (role.is_system && role.code === 'admin') || (targetRole && targetRole.code !== role.code))}
                    onChange={(e) => onChange?.(role.code, record.permission.code, e.target.checked)}
                />
            )
        }))
    ];

    return (
        <Table
            dataSource={rows}
            columns={columns}
            loading={loading}
            pagination={false}
            scroll={{ x: 1000, y: 500 }}
            bordered
            size="small"
            rowClassName={(record, index) => index % 2 === 0 ? "bg-white" : "bg-gray-50"}
        />
    );
};

export default PermissionMatrix;
