"""
Seed bulk fake users for local testing.

This script creates ~50 users distributed by roles and assigns role mappings
in user_roles. It is idempotent by email: existing users are skipped by default.

Examples:
    python migrate/seed_fake_users.py
    python migrate/seed_fake_users.py --admin-count 5 --employee-count 15 --intern-guest-count 30
    python migrate/seed_fake_users.py --reset-existing --password Pass123
"""

import argparse
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from passlib.context import CryptContext
from pymongo import MongoClient


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class BulkUserSeeder:
    def __init__(self, mongodb_url: str, db_name: str, password: str, reset_existing: bool):
        self.mongodb_url = mongodb_url
        self.db_name = db_name
        self.password = password
        self.reset_existing = reset_existing
        self.client: Optional[MongoClient] = None
        self.db = None

    def connect(self) -> None:
        self.client = MongoClient(self.mongodb_url)
        self.db = self.client[self.db_name]
        self.client.admin.command("ping")

    def close(self) -> None:
        if self.client:
            self.client.close()

    def load_role_ids(self) -> Dict[str, object]:
        roles = list(self.db.roles.find({"code": {"$in": ["admin", "employee", "intern_guest"]}}))
        role_ids = {r["code"]: r["_id"] for r in roles}
        missing = [r for r in ["admin", "employee", "intern_guest"] if r not in role_ids]
        if missing:
            raise ValueError(
                f"Missing roles in DB: {missing}. Run seed_database.py first to create system roles."
            )
        return role_ids

    @staticmethod
    def build_user_specs(admin_count: int, employee_count: int, intern_guest_count: int) -> List[Tuple[str, str, str, str]]:
        specs: List[Tuple[str, str, str, str]] = []

        for i in range(1, admin_count + 1):
            email = f"bulk.admin{i:02d}@airc.edu.vn"
            full_name = f"Bulk Admin {i:02d}"
            specs.append((email, full_name, "admin", "Ban Giam Doc"))

        for i in range(1, employee_count + 1):
            email = f"bulk.employee{i:02d}@airc.edu.vn"
            full_name = f"Bulk Employee {i:02d}"
            specs.append((email, full_name, "employee", "Phong Ky Thuat"))

        for i in range(1, intern_guest_count + 1):
            email = f"bulk.intern_guest{i:02d}@airc.edu.vn"
            full_name = f"Bulk InternGuest {i:02d}"
            specs.append((email, full_name, "intern_guest", "Thuc Tap Sinh"))

        return specs

    def run(self, admin_count: int, employee_count: int, intern_guest_count: int) -> None:
        role_ids = self.load_role_ids()
        hashed_password = pwd_context.hash(self.password)

        specs = self.build_user_specs(admin_count, employee_count, intern_guest_count)

        created = 0
        updated = 0
        skipped = 0
        role_stats = {"admin": 0, "employee": 0, "intern_guest": 0}

        for email, full_name, role_code, department in specs:
            role_id = role_ids[role_code]
            existing = self.db.users.find_one({"email": email})

            if existing:
                user_id = existing["_id"]

                if self.reset_existing:
                    self.db.users.update_one(
                        {"_id": user_id},
                        {
                            "$set": {
                                "full_name": full_name,
                                "hashed_password": hashed_password,
                                "role": role_code,
                                "department": department,
                                "is_active": True,
                                "updated_at": datetime.utcnow(),
                            }
                        },
                    )
                    updated += 1
                else:
                    skipped += 1

                # Keep exactly one role mapping for deterministic login behavior.
                self.db.user_roles.delete_many({"user_id": user_id})
                self.db.user_roles.insert_one(
                    {
                        "user_id": user_id,
                        "role_id": role_id,
                        "assigned_at": datetime.utcnow(),
                    }
                )
                role_stats[role_code] += 1
                continue

            now = datetime.utcnow()
            insert_result = self.db.users.insert_one(
                {
                    "email": email,
                    "full_name": full_name,
                    "hashed_password": hashed_password,
                    "role": role_code,
                    "department": department,
                    "is_active": True,
                    "is_verified": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            user_id = insert_result.inserted_id

            self.db.user_roles.insert_one(
                {
                    "user_id": user_id,
                    "role_id": role_id,
                    "assigned_at": now,
                }
            )
            created += 1
            role_stats[role_code] += 1

        print("=" * 72)
        print("BULK USER SEED COMPLETED")
        print("=" * 72)
        print(f"Target users         : {len(specs)}")
        print(f"Created              : {created}")
        print(f"Updated              : {updated}")
        print(f"Skipped              : {skipped}")
        print(f"Role admin total     : {role_stats['admin']}")
        print(f"Role employee total  : {role_stats['employee']}")
        print(f"Role intern_guest total: {role_stats['intern_guest']}")
        print(f"Default password     : {self.password}")
        print("=" * 72)


def resolve_mongodb_url() -> str:
    env_url = os.getenv("MONGODB_URL")
    if env_url:
        return env_url

    in_container = os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")
    return "mongodb://mongodb:27017" if in_container else "mongodb://localhost:27017"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed fake users for RBAC/UI testing")
    parser.add_argument("--admin-count", type=int, default=5)
    parser.add_argument("--employee-count", type=int, default=15)
    parser.add_argument("--intern-guest-count", type=int, default=30)
    parser.add_argument("--password", type=str, default="Pass123")
    parser.add_argument(
        "--reset-existing",
        action="store_true",
        help="Update password/name for existing bulk users instead of skipping",
    )
    parser.add_argument("--db-name", type=str, default=os.getenv("MONGODB_DB_NAME", "airc_auth_db"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    employee_count = args.employee_count
    intern_guest_count = args.intern_guest_count

    if args.admin_count < 0 or employee_count < 0 or intern_guest_count < 0:
        raise ValueError("Counts must be non-negative")

    mongodb_url = resolve_mongodb_url()

    print(f"Using MongoDB URL: {mongodb_url}")
    print(f"Using DB name    : {args.db_name}")

    seeder = BulkUserSeeder(
        mongodb_url=mongodb_url,
        db_name=args.db_name,
        password=args.password,
        reset_existing=args.reset_existing,
    )

    try:
        seeder.connect()
        seeder.run(
            admin_count=args.admin_count,
            employee_count=employee_count,
            intern_guest_count=intern_guest_count,
        )
    finally:
        seeder.close()


if __name__ == "__main__":
    main()
