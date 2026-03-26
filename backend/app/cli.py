import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select

from app.core.auth import hash_password
from app.database import async_session, engine, wait_for_db
from app.models.user import User


async def list_users() -> None:
    await wait_for_db()
    async with async_session() as session:
        result = await session.execute(
            select(User).order_by(User.id)
        )
        users = result.scalars().all()

    if not users:
        print("No users found.")
        return

    print(f"{'ID':<6}{'Username':<30}{'Admin':<8}{'Created'}")
    print("-" * 70)
    for u in users:
        created = u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "—"
        print(f"{u.id:<6}{u.username:<30}{'yes' if u.is_admin else 'no':<8}{created}")

    await engine.dispose()


async def reset_password(username: str, password: str) -> None:
    await wait_for_db()
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        if user is None:
            print(f"Error: user '{username}' not found.")
            await engine.dispose()
            sys.exit(1)

        user.password_hash = hash_password(password)
        await session.commit()

    print(f"Password reset for user '{username}'.")
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Package Tracker admin CLI",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list-users", help="List all users with their roles")

    rp = sub.add_parser("reset-password", help="Reset a user's password")
    rp.add_argument("username", help="Username to reset")
    rp.add_argument("--password", help="New password (prompted if omitted)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "list-users":
        asyncio.run(list_users())

    elif args.command == "reset-password":
        password = args.password
        if password is None:
            password = getpass.getpass("New password: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("Error: passwords do not match.")
                sys.exit(1)
        if not password:
            print("Error: password cannot be empty.")
            sys.exit(1)
        asyncio.run(reset_password(args.username, password))


if __name__ == "__main__":
    main()
