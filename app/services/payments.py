from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Order, PaymentReceipt, AdminAuditLog

class PaymentTransitionError(ValueError):
    pass

async def review_receipt(session: AsyncSession, order_id: int, admin_id: int, approve: bool) -> Order:
    """Transaction-safe conditional state transition; duplicate reviews fail closed."""
    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if not order or order.payment_status != 'UNDER_REVIEW':
        raise PaymentTransitionError('این سفارش در انتظار بررسی نیست.')
    receipt = await session.scalar(select(PaymentReceipt).where(PaymentReceipt.order_id == order_id, PaymentReceipt.status == 'UNDER_REVIEW').with_for_update())
    if not receipt:
        raise PaymentTransitionError('رسید قابل بررسی برای این سفارش وجود ندارد.')
    now = datetime.now(timezone.utc)
    order.payment_status = 'PAID' if approve else 'REJECTED'
    receipt.status = 'APPROVED' if approve else 'REJECTED'
    receipt.reviewed_by = admin_id
    receipt.reviewed_at = now
    session.add(AdminAuditLog(admin_id=admin_id, action='receipt_approved' if approve else 'receipt_rejected', target_type='order', target_id=str(order_id), timestamp=now))
    await session.flush()
    return order
