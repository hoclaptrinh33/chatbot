"""
Backfill department field for existing users.

Usage:
    python migrate/seed_user_departments.py
    python migrate/seed_user_departments.py --overwrite
"""

import argparse
import os
from datetime import datetime
from typing import Optional

from pymongo import MongoClient


DEFAULT_DEPARTMENT_BY_ROLE = {
    "admin": "Ban Giam Doc",
    "employee": "Phong Ky Thuat",
    "intern_guest": "Thuc Tap Sinh",
}


def resolve_mongodb_url() -> str:
    env_url = os.getenv("MONGODB_URL")
    if env_url:
        return env_url

    in_container = os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")
    return "mongodb://mongodb:27017" if in_container else "mongodb://localhost:27017"


def get_user_role_code(db, user_id) -> str:
    user_role = db.user_roles.find_one({"user_id": user_id})
    if not user_role:
        return "intern_guest"

    role = db.roles.find_one({"_id": user_role["role_id"]})
    if not role:
        return "intern_guest"

    return role.get("code", "intern_guest")


def run(mongodb_url: str, db_name: str, overwrite: bool) -> None:
    client: Optional[MongoClient] = None
    try:
        client = MongoClient(mongodb_url)
        db = client[db_name]
        client.admin.command("ping")

        updated = 0
        skipped = 0

        for user in db.users.find({}):
            has_department = bool(user.get("department"))
            if has_department and not overwrite:
                skipped += 1
                continue

            role_code = get_user_role_code(db, user["_id"])
            department = DEFAULT_DEPARTMENT_BY_ROLE.get(role_code, "Khac")

            db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "department": department,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            updated += 1

        print("=" * 64)
        print("USER DEPARTMENT BACKFILL COMPLETED")
        print("=" * 64)
        print(f"Database: {db_name}")
        print(f"Updated users: {updated}")
        print(f"Skipped users: {skipped}")
        print("=" * 64)
    finally:
        if client:
            client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill department for existing users")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite department if already set")
    parser.add_argument("--db-name", type=str, default=os.getenv("MONGODB_DB_NAME", "airc_auth_db"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mongodb_url = resolve_mongodb_url()

    print(f"Using MongoDB URL: {mongodb_url}")
    print(f"Using DB name    : {args.db_name}")
    print(f"Overwrite mode   : {args.overwrite}")

    run(
        mongodb_url=mongodb_url,
        db_name=args.db_name,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
