"""
RBAC Repository - Database operations cho RBAC system

Repository cho:
- Permissions CRUD
- Roles CRUD  
- Role-Permission mapping
- User-Role assignment
- Permission queries
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.rbac import *
from bson import ObjectId
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RBACRepository:
    """
    Repository xử lý tất cả database operations cho RBAC
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.permissions = db.permissions
        self.roles = db.roles
        self.role_permissions = db.role_permissions
        self.user_roles = db.user_roles
    
    # ==================== PERMISSIONS ====================
    
    async def create_permission(
        self, 
        perm: PermissionCreate, 
        created_by: Optional[str] = None
    ) -> PermissionResponse:
        """
        Tạo permission mới
        
        Args:
            perm: Permission data
            created_by: User ID (None cho system permissions)
            
        Returns:
            PermissionResponse với ID mới
        """
        doc = perm.model_dump()
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        doc["created_by"] = ObjectId(created_by) if created_by else None
        
        result = await self.permissions.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        
        logger.info(f"Created permission: {perm.code}")
        return PermissionResponse(**doc)
    
    async def get_all_permissions(
        self, 
        include_system: bool = True
    ) -> List[PermissionResponse]:
        """
        Lấy tất cả permissions
        
        Args:
            include_system: Include system permissions (default True)
            
        Returns:
            List of permissions
        """
        query = {} if include_system else {"is_system": False}
        cursor = self.permissions.find(query)
        
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(PermissionResponse(**doc))
        
        return results
    
    async def get_permission_by_id(self, permission_id: str) -> Optional[PermissionResponse]:
        """Get permission by ID"""
        doc = await self.permissions.find_one({"_id": ObjectId(permission_id)})
        if not doc:
            return None
        
        doc["_id"] = str(doc["_id"])
        return PermissionResponse(**doc)
    
    async def get_permission_by_code(self, code: str) -> Optional[PermissionResponse]:
        """Get permission by code"""
        doc = await self.permissions.find_one({"code": code})
        if not doc:
            return None
        
        doc["_id"] = str(doc["_id"])
        return PermissionResponse(**doc)
    
    async def update_permission(
        self, 
        permission_id: str, 
        update_data: PermissionUpdate
    ) -> Optional[PermissionResponse]:
        """
        Cập nhật permission
        
        Note: Chỉ cho phép sửa name và description
        """
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return await self.get_permission_by_id(permission_id)
        
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await self.permissions.find_one_and_update(
            {"_id": ObjectId(permission_id)},
            {"$set": update_dict},
            return_document=True
        )
        
        if not result:
            return None
        
        result["_id"] = str(result["_id"])
        return PermissionResponse(**result)
    
    async def delete_permission(self, permission_id: str) -> bool:
        """
        Xóa permission (chỉ non-system permissions)
        
        Returns:
            True nếu xóa thành công
        """
        # Check if system permission
        perm = await self.get_permission_by_id(permission_id)
        if not perm or perm.is_system:
            return False
        
        # Delete from role_permissions first
        await self.role_permissions.delete_many({"permission_id": ObjectId(permission_id)})
        
        # Delete permission
        result = await self.permissions.delete_one({"_id": ObjectId(permission_id)})
        return result.deleted_count > 0
    
    # ==================== ROLES ====================
    
    async def create_role(
        self, 
        role: RoleCreate, 
        created_by: Optional[str] = None
    ) -> RoleResponse:
        """Tạo role mới"""
        doc = role.model_dump()
        doc["is_active"] = True
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        doc["created_by"] = ObjectId(created_by) if created_by else None
        
        result = await self.roles.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        doc["permission_count"] = 0
        
        logger.info(f"Created role: {role.code}")
        return RoleResponse(**doc)
    
    async def get_all_roles(
        self, 
        include_inactive: bool = False
    ) -> List[RoleResponse]:
        """Lấy tất cả roles"""
        query = {} if include_inactive else {"is_active": True}
        cursor = self.roles.find(query)
        roles = await cursor.to_list(None)
        
        results = []
        for role in roles:
            # Count permissions
            role_id_obj = role["_id"]
            perm_count = await self.role_permissions.count_documents({"role_id": role_id_obj})
            print(f"[DEBUG] Role: {role.get('code')} | ID: {role_id_obj} ({type(role_id_obj)}) | Count: {perm_count}")
            
            # Convert ObjectId to string for Pydantic
            role["_id"] = str(role["_id"])
            role["permission_count"] = perm_count
            results.append(RoleResponse(**role))
        
        return results
    
    async def get_role_by_id(self, role_id: str) -> Optional[RoleResponse]:
        """Get role by ID"""
        doc = await self.roles.find_one({"_id": ObjectId(role_id)})
        if not doc:
            return None
        
        perm_count = await self.role_permissions.count_documents({"role_id": ObjectId(role_id)})
        doc["_id"] = str(doc["_id"])
        doc["permission_count"] = perm_count
        return RoleResponse(**doc)
    
    async def get_role_by_code(self, code: str) -> Optional[RoleResponse]:
        """Get role by code"""
        doc = await self.roles.find_one({"code": code})
        if not doc:
            return None
        
        perm_count = await self.role_permissions.count_documents({"role_id": doc["_id"]})
        doc["_id"] = str(doc["_id"])
        doc["permission_count"] = perm_count
        return RoleResponse(**doc)
    
    async def get_role_with_permissions(
        self, 
        role_id: str
    ) -> Optional[RoleWithPermissions]:
        """
        Get role với danh sách permissions
        
        Sử dụng aggregation pipeline để join với permissions
        """
        pipeline = [
            {"$match": {"_id": ObjectId(role_id)}},
            {"$lookup": {
                "from": "role_permissions",
                "localField": "_id",
                "foreignField": "role_id",
                "as": "role_perms"
            }},
            {"$lookup": {
                "from": "permissions",
                "localField": "role_perms.permission_id",
                "foreignField": "_id",
                "as": "permissions"
            }},
            {"$addFields": {
                "permission_count": {"$size": "$permissions"}
            }}
        ]
        
        cursor = self.roles.aggregate(pipeline)
        docs = await cursor.to_list(1)
        
        if not docs:
            return None
        
        doc = docs[0]
        doc["_id"] = str(doc["_id"])
        
        # Convert permission ObjectIds to strings
        for perm in doc.get("permissions", []):
            perm["_id"] = str(perm["_id"])
        
        return RoleWithPermissions(**doc)
    
    async def update_role(
        self, 
        role_id: str, 
        update_data: RoleUpdate
    ) -> Optional[RoleResponse]:
        """Cập nhật role"""
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return await self.get_role_by_id(role_id)
        
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await self.roles.find_one_and_update(
            {"_id": ObjectId(role_id)},
            {"$set": update_dict},
            return_document=True
        )
        
        if not result:
            return None
        
        perm_count = await self.role_permissions.count_documents({"role_id": ObjectId(role_id)})
        result["_id"] = str(result["_id"])
        result["permission_count"] = perm_count
        return RoleResponse(**result)
    
    async def delete_role(self, role_id: str) -> bool:
        """
        Xóa role (chỉ non-system roles)
        
        Also deletes all role_permissions và user_roles
        """
        # Check if system role
        role = await self.get_role_by_id(role_id)
        if not role or role.is_system:
            return False
        
        # Delete mappings
        await self.role_permissions.delete_many({"role_id": ObjectId(role_id)})
        await self.user_roles.delete_many({"role_id": ObjectId(role_id)})
        
        # Delete role
        result = await self.roles.delete_one({"_id": ObjectId(role_id)})
        return result.deleted_count > 0
    
    # ==================== ROLE-PERMISSION MAPPING ====================
    
    async def grant_permissions_to_role(
        self, 
        role_id: str, 
        permission_ids: List[str],
        granted_by: Optional[str] = None
    ):
        """
        Grant multiple permissions to role
        
        Sử dụng insert_many với ignore duplicates
        """
        if not permission_ids:
            return

        docs = []
        for pid in permission_ids:
            docs.append({
                "role_id": ObjectId(role_id),
                "permission_id": ObjectId(pid),
                "granted_at": datetime.utcnow(),
                "granted_by": ObjectId(granted_by) if granted_by else None
            })
        
        if docs:
            try:
                await self.role_permissions.insert_many(docs, ordered=False)
            except Exception as e:
                # Ignore duplicate key errors
                if "duplicate" not in str(e).lower():
                    raise
        
        logger.info(f"Granted {len(permission_ids)} permissions to role {role_id}")

    async def set_role_permissions(
        self,
        role_id: str,
        permission_ids: List[str],
        assigned_by: Optional[str] = None
    ):
        """
        Set permissions for a role (Replace existing)
        
        1. Delete all existing permissions for role
        2. Insert new permissions
        """
        # 1. Clear existing
        await self.role_permissions.delete_many({"role_id": ObjectId(role_id)})
        
        # 2. Grant new ones
        if permission_ids:
            await self.grant_permissions_to_role(role_id, permission_ids, assigned_by)
            
        logger.info(f"Set {len(permission_ids)} permissions for role {role_id}")
    
    async def revoke_permission_from_role(
        self, 
        role_id: str, 
        permission_id: str
    ) -> bool:
        """Revoke permission from role"""
        result = await self.role_permissions.delete_one({
            "role_id": ObjectId(role_id),
            "permission_id": ObjectId(permission_id)
        })
        
        return result.deleted_count > 0
    
    async def get_role_permissions(self, role_id: str) -> List[PermissionResponse]:
        """Get all permissions của một role"""
        pipeline = [
            {"$match": {"role_id": ObjectId(role_id)}},
            {"$lookup": {
                "from": "permissions",
                "localField": "permission_id",
                "foreignField": "_id",
                "as": "permission"
            }},
            {"$unwind": "$permission"},
            {"$replaceRoot": {"newRoot": "$permission"}}
        ]
        
        cursor = self.role_permissions.aggregate(pipeline)
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(PermissionResponse(**doc))
        
        return results
    
    # ==================== USER-ROLE ASSIGNMENT ====================
    
    async def assign_role_to_user(
        self, 
        user_id: str, 
        role_id: str,
        assigned_by: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ):
        """Assign role to user"""
        doc = {
            "user_id": ObjectId(user_id),
            "role_id": ObjectId(role_id),
            "assigned_at": datetime.utcnow(),
            "assigned_by": ObjectId(assigned_by) if assigned_by else None,
            "expires_at": expires_at
        }
        
        # Use upsert to avoid duplicates
        await self.user_roles.update_one(
            {"user_id": ObjectId(user_id), "role_id": ObjectId(role_id)},
            {"$set": doc},
            upsert=True
        )
        
        logger.info(f"Assigned role {role_id} to user {user_id}")
    
    async def remove_role_from_user(
        self, 
        user_id: str, 
        role_id: str
    ) -> bool:
        """Remove role from user"""
        result = await self.user_roles.delete_one({
            "user_id": ObjectId(user_id),
            "role_id": ObjectId(role_id)
        })
        
        return result.deleted_count > 0
    
    async def get_user_roles(self, user_id: str) -> List[RoleResponse]:
        """
        Get all active roles of a user
        
        Filters out expired roles
        """
        pipeline = [
            {"$match": {
                "user_id": ObjectId(user_id),
                "$or": [
                    {"expires_at": None},
                    {"expires_at": {"$gt": datetime.utcnow()}}
                ]
            }},
            {"$lookup": {
                "from": "roles",
                "localField": "role_id",
                "foreignField": "_id",
                "as": "role"
            }},
            {"$unwind": "$role"},
            {"$match": {"role.is_active": True}},
            {"$replaceRoot": {"newRoot": "$role"}}
        ]
        
        cursor = self.user_roles.aggregate(pipeline)
        results = []
        async for doc in cursor:
            perm_count = await self.role_permissions.count_documents({"role_id": doc["_id"]})
            doc["_id"] = str(doc["_id"])
            doc["permission_count"] = perm_count
            results.append(RoleResponse(**doc))
        
        return results
    
    async def get_user_permissions(self, user_id: str) -> List[PermissionResponse]:
        """
        Get ALL unique permissions của user (từ tất cả roles)
        
        Sử dụng aggregation pipeline phức tạp:
        1. Get user roles (active, not expired)
        2. Join với role_permissions
        3. Join với permissions
        4. Remove duplicates
        """
        pipeline = [
            # Match user roles
            {"$match": {
                "user_id": ObjectId(user_id),
                "$or": [
                    {"expires_at": None},
                    {"expires_at": {"$gt": datetime.utcnow()}}
                ]
            }},
            # Join with active roles only
            {"$lookup": {
                "from": "roles",
                "localField": "role_id",
                "foreignField": "_id",
                "as": "role"
            }},
            {"$unwind": "$role"},
            {"$match": {"role.is_active": True}},
            # Join with role_permissions
            {"$lookup": {
                "from": "role_permissions",
                "localField": "role_id",
                "foreignField": "role_id",
                "as": "role_perms"
            }},
            {"$unwind": "$role_perms"},
            # Join with permissions
            {"$lookup": {
                "from": "permissions",
                "localField": "role_perms.permission_id",
                "foreignField": "_id",
                "as": "permission"
            }},
            {"$unwind": "$permission"},
            # Remove duplicates
            {"$group": {
                "_id": "$permission._id",
                "permission": {"$first": "$permission"}
            }},
            {"$replaceRoot": {"newRoot": "$permission"}}
        ]
        
        cursor = self.user_roles.aggregate(pipeline)
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(PermissionResponse(**doc))
        
        return results
