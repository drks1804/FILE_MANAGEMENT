from app.database.database import SessionLocal
from app.database.models import RefreshToken,File
from app.service.utils import utc_now
from datetime import timedelta
from app.handlers.recycle_bin_handler import permanently_delete_file_handler


def delete_expired_refresh_tokens():

    db = SessionLocal()

    try:

        deleted_count = (
            db.query(RefreshToken)
            .filter(RefreshToken.expires_at <= utc_now())
            .delete(synchronize_session=False)
        )

        db.commit()

        print(f"Deleted {deleted_count} expired refresh tokens.")

    except Exception as e:
        db.rollback()
        print(f"Error deleting expired refresh tokens: {e}")

    finally:
        db.close()

def recycle_bin_cleanup():

    db = SessionLocal()

    try:
        expire_time = utc_now() - timedelta(days=30)

        expired_files = (
            db.query(File)
            .filter(
                File.deleted_at.is_not(None),
                File.deleted_at <= expire_time
            )
            .all()
        )

        for file in expired_files:

            try:
                permanently_delete_file_handler(
                    file_id=file.file_id,
                    user_id=file.user_id,
                    db=db
                )

                print(f"Permanently deleted {file.file_id}")

            except Exception as e:
                db.rollback()

                print(
                    f"Failed to permanently delete "
                    f"{file.file_id}: {e}"
                )

    except Exception as e:
        db.rollback()
        print(f"Recycle Bin cleanup error: {e}")

    finally:
        db.close()




