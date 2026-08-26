import argparse

from sqlalchemy import select

from backend.app.core.config import get_web_settings
from backend.app.core.database import SessionLocal
from backend.app.core.errors import ApiError
from backend.app.models.user import AppUser, UserRole, UserStatus
from backend.app.services.auth_service import create_invitation
from backend.app.services.mail_service import create_mail_sender


def bootstrap_admin(email: str) -> None:
    """在系统尚无管理员时生成首个管理员邀请。"""
    settings = get_web_settings()
    mail_sender = create_mail_sender(settings)
    with SessionLocal() as db:
        existing_admin = db.scalar(
            select(AppUser).where(
                AppUser.role == UserRole.ADMIN,
                AppUser.status.in_([UserStatus.INVITED, UserStatus.ACTIVE]),
            )
        )
        if existing_admin is not None:
            raise ApiError(409, "ADMIN_ALREADY_EXISTS", "管理员已经初始化")
        create_invitation(
            db,
            email,
            UserRole.ADMIN,
            created_by=None,
            settings=settings,
            mail_sender=mail_sender,
        )
    print("首个管理员邀请已创建")


def main() -> None:
    """解析 Web 服务运维命令。"""
    parser = argparse.ArgumentParser(description="积加数据同步 Web 服务运维命令")
    subparsers = parser.add_subparsers(dest="command", required=True)
    bootstrap_parser = subparsers.add_parser("bootstrap-admin", help="创建首个管理员邀请")
    bootstrap_parser.add_argument("--email", required=True, help="管理员邮箱")
    args = parser.parse_args()

    try:
        if args.command == "bootstrap-admin":
            bootstrap_admin(args.email)
    except ApiError as error:
        parser.error(error.message)


if __name__ == "__main__":
    main()
