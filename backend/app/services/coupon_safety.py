import re
from datetime import datetime, timezone

def ml_product_code(offer: dict) -> str | None:
    for value in (offer.get('ml_code'), offer.get('product_id'), offer.get('product_url')):
        match = re.search(r'(?<![A-Z0-9])(MLBU?-?\d+)(?![A-Z0-9])', str(value or '').upper())
        if match:
            return match.group(1).replace('-', '')
    return None

def coupon_is_current(coupon: dict, now: datetime | None = None) -> bool:
    if not coupon.get('verified'):
        return False
    expires = coupon.get('expires_at')
    if isinstance(expires, str):
        try:
            expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
        except ValueError:
            return False
    if not isinstance(expires, datetime):
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires > (now or datetime.now(timezone.utc))

def coupon_notice(coupon: dict | None) -> str:
    if not coupon or not coupon_is_current(coupon):
        return ''
    code = str(coupon.get('code') or '')
    lines = []
    if code.startswith('MLC-'):
        lines.append('Cupom de ativação na conta do Mercado Livre; não há código para digitar.')
    elif code:
        lines.append(f'Código informado pela loja: {code}')
    if coupon.get('discount_text'):
        lines.append(f"Desconto anunciado: {coupon['discount_text']}")
    if coupon.get('conditions'):
        lines.append(f"Condições: {coupon['conditions']}")
    lines.append('Confira elegibilidade, limite, validade e preço final na loja antes de comprar.')
    return '\n'.join(lines)

def coupon_from_offer(offer: dict) -> dict:
    return {'verified': offer.get('coupon_verified', False), 'code': offer.get('coupon_code'),
            'discount_text': offer.get('coupon_discount'), 'conditions': offer.get('coupon_conditions'),
            'expires_at': offer.get('coupon_expires_at')}
